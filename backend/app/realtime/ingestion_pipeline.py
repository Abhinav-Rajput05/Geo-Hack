from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from app.ingestion.news_ingestor import FeedSource, news_ingestor
from app.realtime.event_producer import redis_event_producer

logger = logging.getLogger(__name__)


class RealtimeIngestionPipeline:
    """Event-driven ingestion pipeline: fetch -> process -> store -> publish."""

    def __init__(self) -> None:
        self.processor_workers = 4
        self.store_workers = 4

    async def run_once(self, limit_per_source: int = 50, category: Optional[str] = None) -> Dict[str, Any]:
        feeds = news_ingestor.load_feeds(category=category)

        raw_queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
        normalized_queue: asyncio.Queue = asyncio.Queue(maxsize=2000)

        counters: Dict[str, int] = {
            "fetched": 0,
            "deduplicated": 0,
            "stored": 0,
            "published": 0,
            "failed_feeds": 0,
        }
        stored_articles: List[Dict[str, Any]] = []
        failures: Dict[str, str] = {}
        counter_lock = asyncio.Lock()
        seen_lock = asyncio.Lock()

        news_ingestor._load_seen_hashes()

        processor_tasks = [
            asyncio.create_task(
                self._processor_worker(
                    raw_queue=raw_queue,
                    normalized_queue=normalized_queue,
                    counters=counters,
                    counter_lock=counter_lock,
                    seen_lock=seen_lock,
                )
            )
            for _ in range(self.processor_workers)
        ]
        store_tasks = [
            asyncio.create_task(
                self._store_worker(
                    normalized_queue=normalized_queue,
                    counters=counters,
                    stored_articles=stored_articles,
                    counter_lock=counter_lock,
                )
            )
            for _ in range(self.store_workers)
        ]

        await self._fetch_all(feeds, raw_queue, counters, failures, counter_lock, limit_per_source, category)

        for _ in range(self.processor_workers):
            await raw_queue.put(None)
        await asyncio.gather(*processor_tasks)

        for _ in range(self.store_workers):
            await normalized_queue.put(None)
        await asyncio.gather(*store_tasks)

        news_ingestor._persist_seen_hashes()

        logger.info(
            "[SUMMARY] feeds_processed=%s fetched=%s deduped=%s stored=%s published=%s",
            len(feeds),
            counters["fetched"],
            counters["deduplicated"],
            counters["stored"],
            counters["published"],
        )
        if counters["fetched"] == 0:
            logger.warning("[SUMMARY] 0 articles fetched from all configured sources")

        return {
            "total_feeds_processed": len(feeds),
            "total_articles": counters["fetched"],
            "unique_articles": counters["deduplicated"],
            "persisted_to_neo4j": counters["stored"],
            "published_events": counters["published"],
            "source_failures": failures,
            "articles": stored_articles,
        }

    async def _fetch_all(
        self,
        feeds: List[FeedSource],
        raw_queue: asyncio.Queue,
        counters: Dict[str, int],
        failures: Dict[str, str],
        counter_lock: asyncio.Lock,
        limit_per_source: int,
        category: Optional[str],
    ) -> None:
        timeout = aiohttp.ClientTimeout(total=news_ingestor.fetch_timeout_seconds)
        headers = {"User-Agent": "global-ontology-engine/3.0"}
        connector = aiohttp.TCPConnector(limit=news_ingestor.max_concurrent_fetches, ttl_dns_cache=300)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
            feed_tasks = [
                asyncio.create_task(
                    self._fetch_feed_to_queue(
                        session=session,
                        feed=feed,
                        raw_queue=raw_queue,
                        counters=counters,
                        failures=failures,
                        counter_lock=counter_lock,
                        limit_per_source=limit_per_source,
                    )
                )
                for feed in feeds
            ]
            await asyncio.gather(*feed_tasks)

        # Optional NewsAPI source
        newsapi_articles = await news_ingestor._fetch_newsapi_async(limit_per_source=limit_per_source, category=category)
        for article in newsapi_articles:
            await raw_queue.put(article)
        if newsapi_articles:
            async with counter_lock:
                counters["fetched"] += len(newsapi_articles)

    async def _fetch_feed_to_queue(
        self,
        session: aiohttp.ClientSession,
        feed: FeedSource,
        raw_queue: asyncio.Queue,
        counters: Dict[str, int],
        failures: Dict[str, str],
        counter_lock: asyncio.Lock,
        limit_per_source: int,
    ) -> None:
        fetched_feed, payload, error_text = await news_ingestor._fetch_single_feed(
            session=session,
            feed=feed,
            limit_per_source=limit_per_source,
        )

        if error_text:
            failures[fetched_feed.name] = error_text
            async with counter_lock:
                counters["failed_feeds"] += 1
            logger.error("[ERROR] Feed failed: %s", fetched_feed.name)
            return

        parsed_articles = news_ingestor.parse_articles(fetched_feed, payload, limit_per_source=limit_per_source)
        for article in parsed_articles:
            await raw_queue.put(article)

        async with counter_lock:
            counters["fetched"] += len(parsed_articles)

    async def _processor_worker(
        self,
        raw_queue: asyncio.Queue,
        normalized_queue: asyncio.Queue,
        counters: Dict[str, int],
        counter_lock: asyncio.Lock,
        seen_lock: asyncio.Lock,
    ) -> None:
        while True:
            article = await raw_queue.get()
            if article is None:
                raw_queue.task_done()
                break

            article_hash = news_ingestor._build_article_hash(article.get("title", ""), article.get("url", ""))
            async with seen_lock:
                if article_hash in news_ingestor._seen_hashes:
                    raw_queue.task_done()
                    continue
                news_ingestor._seen_hashes.add(article_hash)
            article["id"] = article_hash
            normalized = news_ingestor.normalize_articles([article])[0]
            await normalized_queue.put(normalized)

            async with counter_lock:
                counters["deduplicated"] += 1

            raw_queue.task_done()

    async def _store_worker(
        self,
        normalized_queue: asyncio.Queue,
        counters: Dict[str, int],
        stored_articles: List[Dict[str, Any]],
        counter_lock: asyncio.Lock,
    ) -> None:
        while True:
            article = await normalized_queue.get()
            if article is None:
                normalized_queue.task_done()
                break

            stored = await news_ingestor.store_in_neo4j([article])
            if stored > 0:
                stored_articles.append(article)
                async with counter_lock:
                    counters["stored"] += 1

                published = await redis_event_producer.publish_article_event(article)
                if published:
                    async with counter_lock:
                        counters["published"] += 1

            normalized_queue.task_done()


realtime_ingestion_pipeline = RealtimeIngestionPipeline()
