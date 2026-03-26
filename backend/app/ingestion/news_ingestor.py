"""
Production-ready news ingestion pipeline.

Pipeline steps:
- load_feeds()
- fetch_all_feeds_async()
- parse_articles()
- deduplicate_articles()
- normalize_articles()
- store_in_neo4j()
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
import feedparser
from dateutil import parser as date_parser

from app.config import settings
from app.database.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    category: str


DEFAULT_FEEDS_PATH = Path(__file__).with_name("rss_feeds.json")
TEMP_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]


class NewsIngestor:
    """Scalable async news ingestion service with robust Neo4j persistence."""

    def __init__(self) -> None:
        self.newsapi_key = settings.news_api_key
        self.fetch_timeout_seconds = int(getattr(settings, "NEWS_FETCH_TIMEOUT_SECONDS", 8))
        self.max_concurrent_fetches = int(getattr(settings, "NEWS_MAX_CONCURRENT_FETCHES", 12))
        self.fetch_retries = int(getattr(settings, "NEWS_FETCH_RETRIES", 3))
        self.max_articles_per_feed = int(getattr(settings, "MAX_ARTICLES_PER_INGESTION", 150))
        self.rate_limit_per_second = float(getattr(settings, "NEWS_RATE_LIMIT_PER_SECOND", 8.0))
        self.seen_hashes_file = Path(getattr(settings, "NEWS_SEEN_HASHES_FILE", "data/seen_article_hashes.txt"))
        self.feeds_path = Path(getattr(settings, "NEWS_FEEDS_CONFIG_PATH", str(DEFAULT_FEEDS_PATH)))

        self._fetch_semaphore = asyncio.Semaphore(self.max_concurrent_fetches)
        self._rate_lock = asyncio.Lock()
        self._last_request_ts = 0.0

        self._seen_hashes: Set[str] = set()
        self._seen_loaded = False
        self._neo4j_constraints_ready = False

    async def ingest_all(
        self,
        limit_per_source: int = 50,
        keywords: Optional[List[str]] = None,
        country: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run modular ingestion pipeline while preserving legacy response shape."""
        _ = (keywords, country)  # Reserved for future filters.
        try:
            from app.ingestion.pipeline import ingestion_pipeline

            result = await ingestion_pipeline.run_once(
                limit_per_source=limit_per_source,
                category=category,
            )
            result["total_articles_unique"] = result.get("unique_articles", 0)
            return result
        except Exception as e:
            print(f"[ERROR] Feed failed: ingest_all, Error: {e}")
            logger.error("[ERROR] Ingestion failed: %s", e)
            return {
                "total_articles": 0,
                "unique_articles": 0,
                "total_feeds_processed": 0,
                "total_articles_fetched": 0,
                "total_articles_unique": 0,
                "persisted_to_neo4j": 0,
                "source_failures": {"ingest_all": str(e)},
                "source_counts": {},
                "sources": [],
                "processing_seconds": 0,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "articles": [],
            }

    def load_feeds(self, category: Optional[str] = None) -> List[FeedSource]:
        """Load feed list from JSON config with fallback to settings.RSS_FEEDS."""
        loaded_feeds: List[FeedSource] = []

        config_path = self.feeds_path
        if not config_path.is_absolute():
            # Resolve relative to backend app directory.
            config_path = (Path(__file__).resolve().parents[2] / config_path).resolve()

        if config_path.exists():
            try:
                entries = json.loads(config_path.read_text(encoding="utf-8"))
                for row in entries:
                    if not isinstance(row, dict):
                        continue
                    name = str(row.get("name", "Unknown Feed")).strip()
                    url = str(row.get("url", "")).strip()
                    feed_category = str(row.get("category", "general")).strip().lower()
                    if name and url:
                        loaded_feeds.append(FeedSource(name=name, url=url, category=feed_category))
            except Exception as exc:
                logger.error("[ERROR] Failed to load feeds config from %s: %s", config_path, exc)

        if not loaded_feeds:
            fallback_urls = list(getattr(settings, "RSS_FEEDS", [])) or TEMP_FEEDS
            for url in fallback_urls:
                if isinstance(url, str) and url.strip():
                    loaded_feeds.append(FeedSource(name=url, url=url.strip(), category="general"))

        if category:
            category_normalized = category.strip().lower()
            loaded_feeds = [f for f in loaded_feeds if f.category == category_normalized]

        logger.info("[INGEST] Loaded %s RSS feeds", len(loaded_feeds))
        return loaded_feeds

    async def fetch_all_feeds_async(
        self,
        feeds: List[FeedSource],
        limit_per_source: int,
    ) -> Tuple[List[Tuple[FeedSource, bytes]], Dict[str, str]]:
        """Fetch all RSS feeds in parallel with retry and timeout handling."""
        timeout = aiohttp.ClientTimeout(total=self.fetch_timeout_seconds)
        headers = {"User-Agent": "Mozilla/5.0"}
        connector = aiohttp.TCPConnector(limit=self.max_concurrent_fetches, ttl_dns_cache=300)

        results: List[Tuple[FeedSource, bytes]] = []
        failures: Dict[str, str] = {}

        async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
            tasks = [
                asyncio.create_task(self._fetch_single_feed(session=session, feed=feed, limit_per_source=limit_per_source))
                for feed in feeds
            ]
            completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                logger.error("[ERROR] Unexpected feed task failure: %s", item)
                continue
            feed, payload, error_text = item
            if error_text:
                failures[feed.name] = error_text
                logger.error("[ERROR] Feed failed: %s (%s)", feed.name, error_text)
                continue
            results.append((feed, payload))

        return results, failures

    async def _fetch_single_feed(
        self,
        session: aiohttp.ClientSession,
        feed: FeedSource,
        limit_per_source: int,
    ) -> Tuple[FeedSource, bytes, Optional[str]]:
        """Fetch one feed with retries, timeout safety, and basic rate limiting."""
        _ = limit_per_source  # kept for future provider-specific query params
        logger.info("[INGEST] Fetching feed: %s", feed.name)
        print(f"[DEBUG] Fetching feed: {feed.url}")

        for attempt in range(1, self.fetch_retries + 1):
            try:
                async with self._fetch_semaphore:
                    await self._apply_rate_limit()
                    async with session.get(feed.url) as response:
                        print(f"[DEBUG] Status code: {response.status}")
                        response.raise_for_status()
                        payload = await response.read()

                if not payload:
                    raise ValueError("empty response")

                logger.info("[INGEST] Success: %s bytes from %s", len(payload), feed.name)
                return feed, payload, None
            except Exception as exc:
                if attempt >= self.fetch_retries:
                    return feed, b"", str(exc)
                await asyncio.sleep(min(1.5 * attempt, 4.0))

        return feed, b"", "unreachable"

    async def _apply_rate_limit(self) -> None:
        """Simple per-request pacing to avoid aggressive burst traffic."""
        if self.rate_limit_per_second <= 0:
            return

        min_interval = 1.0 / self.rate_limit_per_second
        loop = asyncio.get_running_loop()

        async with self._rate_lock:
            now = loop.time()
            elapsed = now - self._last_request_ts
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request_ts = loop.time()

    def parse_articles(
        self,
        feed: FeedSource,
        payload: bytes,
        limit_per_source: int,
    ) -> List[Dict[str, Any]]:
        """Parse RSS bytes into raw article dicts."""
        articles: List[Dict[str, Any]] = []
        try:
            parsed = feedparser.parse(payload)
            print(f"[DEBUG] Entries found: {len(parsed.entries or [])}")
            if getattr(parsed, "bozo", 0):
                logger.warning("[ERROR] Feed has parsing warnings: %s", feed.name)

            entries = list(parsed.entries or [])[: max(1, limit_per_source)]
            if not entries:
                logger.warning("[INGEST] No entries found for feed: %s", feed.name)
                return articles

            for entry in entries:
                url = str(getattr(entry, "link", "")).strip()
                title = self._clean_text(str(getattr(entry, "title", "")).strip())
                summary = self._clean_text(
                    str(getattr(entry, "summary", "") or getattr(entry, "description", "")).strip()
                )
                if not title or not url:
                    continue

                articles.append(
                    {
                        "title": title,
                        "summary": summary,
                        "source": feed.name,
                        "published_at": self._to_iso8601(getattr(entry, "published", None)),
                        "url": url,
                        "category": feed.category,
                    }
                )

            logger.info("[INGEST] Success: %s articles", len(articles))
            return articles
        except Exception as exc:
            logger.error("[ERROR] Feed parse failed: %s (%s)", feed.name, exc)
            return []

    def deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates via hash(title + url), including previously-seen entries."""
        self._load_seen_hashes()

        unique_articles: List[Dict[str, Any]] = []
        removed = 0

        for article in articles:
            article_hash = self._build_article_hash(article.get("title", ""), article.get("url", ""))
            if article_hash in self._seen_hashes:
                removed += 1
                continue

            article["id"] = article_hash
            self._seen_hashes.add(article_hash)
            unique_articles.append(article)

        self._persist_seen_hashes()
        logger.info("[DEDUP] Removed %s duplicates", removed)
        return unique_articles

    def normalize_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize into canonical article schema."""
        normalized: List[Dict[str, Any]] = []
        for article in articles:
            normalized.append(
                {
                    "id": article["id"],
                    "title": str(article.get("title", "")).strip(),
                    "summary": str(article.get("summary", "")).strip(),
                    "source": str(article.get("source", "Unknown")).strip(),
                    "published_at": self._to_iso8601(article.get("published_at")),
                    "url": str(article.get("url", "")).strip(),
                    "category": str(article.get("category", "general")).strip().lower(),
                }
            )
        return normalized

    async def store_in_neo4j(self, articles: List[Dict[str, Any]]) -> int:
        """Persist normalized articles using MERGE and transactional writes."""
        if not articles:
            logger.warning("[DB] No articles to insert into Neo4j")
            return 0

        try:
            if not neo4j_client.driver:
                await neo4j_client.connect()

            if not self._neo4j_constraints_ready:
                await self._ensure_neo4j_constraints()
                self._neo4j_constraints_ready = True

            query = """
            UNWIND $articles AS article
            MERGE (a:Article {id: article.id})
            ON CREATE SET a.created_at = datetime()
            SET a.title = article.title,
                a.summary = article.summary,
                a.url = article.url,
                a.published_at = article.published_at,
                a.updated_at = datetime()
            MERGE (s:Source {name: article.source})
            MERGE (a)-[:PUBLISHED_BY]->(s)
            MERGE (c:Category {name: article.category})
            MERGE (a)-[:IN_CATEGORY]->(c)
            MERGE (e:Entity {name: article.title, type: 'Event'})
            ON CREATE SET e.created_at = datetime()
            SET e.updated_at = datetime(),
                e.source = article.source,
                e.url = article.url
            MERGE (a)-[:DESCRIBES]->(e)
            """
            await neo4j_client.execute_write(query=query, parameters={"articles": articles})
            logger.info("[DB] Inserted %s articles into Neo4j", len(articles))
            for article in articles:
                name = article.get("title", "")
                if name:
                    print(f"[DEBUG] Inserted entity: {name}")
            return len(articles)
        except Exception as exc:
            logger.error("[DB] Neo4j persistence failed: %s", exc)
            return 0

    async def _ensure_neo4j_constraints(self) -> None:
        """Create idempotent schema constraints for stable MERGE behavior."""
        constraints = [
            "CREATE CONSTRAINT article_id_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT article_url_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.url IS UNIQUE",
            "CREATE CONSTRAINT source_name_unique IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
        ]
        for statement in constraints:
            try:
                await neo4j_client.execute_write(statement)
            except Exception as exc:
                logger.warning("[DB] Constraint setup warning: %s", exc)

    async def _fetch_newsapi_async(self, limit_per_source: int, category: Optional[str]) -> List[Dict[str, Any]]:
        """Optional NewsAPI ingestion for additional coverage."""
        if not self.newsapi_key:
            return []

        endpoint = "https://newsapi.org/v2/top-headlines"
        params: Dict[str, Any] = {
            "apiKey": self.newsapi_key,
            "language": "en",
            "pageSize": max(1, min(limit_per_source, 100)),
        }
        if category:
            params["category"] = category.lower()

        timeout = aiohttp.ClientTimeout(total=self.fetch_timeout_seconds)
        headers = {"User-Agent": "Mozilla/5.0"}

        for attempt in range(1, self.fetch_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with self._fetch_semaphore:
                        await self._apply_rate_limit()
                        async with session.get(endpoint, params=params) as response:
                            response.raise_for_status()
                            data = await response.json()

                if data.get("status") != "ok":
                    raise ValueError(f"unexpected status: {data.get('status')}")

                mapped: List[Dict[str, Any]] = []
                for row in data.get("articles", []):
                    title = self._clean_text(str(row.get("title") or ""))
                    url = str(row.get("url") or "").strip()
                    if not title or not url:
                        continue
                    mapped.append(
                        {
                            "title": title,
                            "summary": self._clean_text(str(row.get("description") or row.get("content") or "")),
                            "source": str((row.get("source") or {}).get("name") or "NewsAPI").strip(),
                            "published_at": self._to_iso8601(row.get("publishedAt")),
                            "url": url,
                            "category": (category or "general").lower(),
                        }
                    )

                logger.info("[INGEST] NewsAPI success: %s articles", len(mapped))
                return mapped
            except Exception as exc:
                if attempt >= self.fetch_retries:
                    logger.error("[ERROR] NewsAPI failed: %s", exc)
                    return []
                await asyncio.sleep(min(1.5 * attempt, 4.0))

        return []

    def _load_seen_hashes(self) -> None:
        if self._seen_loaded:
            return
        self._seen_loaded = True

        path = self.seen_hashes_file
        if not path.is_absolute():
            path = (Path(__file__).resolve().parents[2] / path).resolve()
        self.seen_hashes_file = path

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    item = line.strip()
                    if item:
                        self._seen_hashes.add(item)
        except Exception as exc:
            logger.warning("[DEDUP] Failed loading seen hash file %s: %s", path, exc)

    def _persist_seen_hashes(self) -> None:
        try:
            self.seen_hashes_file.parent.mkdir(parents=True, exist_ok=True)
            self.seen_hashes_file.write_text("\n".join(sorted(self._seen_hashes)), encoding="utf-8")
        except Exception as exc:
            logger.warning("[DEDUP] Failed persisting seen hashes: %s", exc)

    @staticmethod
    def _build_article_hash(title: str, url: str) -> str:
        payload = f"{title.strip().lower()}::{url.strip().lower()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _to_iso8601(value: Any) -> str:
        if not value:
            return datetime.now(timezone.utc).isoformat()
        try:
            return date_parser.parse(str(value)).astimezone(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.replace("\n", " ").replace("\r", " ").split())

    @staticmethod
    def _count_by_source(articles: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for article in articles:
            source = article.get("source", "Unknown")
            counts[source] = counts.get(source, 0) + 1
        return counts


news_ingestor = NewsIngestor()


def load_feeds() -> List[Dict[str, str]]:
    return [feed.__dict__ for feed in news_ingestor.load_feeds()]


async def fetch_all_feeds_async() -> List[Tuple[Dict[str, str], int]]:
    feeds = news_ingestor.load_feeds()
    results, _ = await news_ingestor.fetch_all_feeds_async(feeds, limit_per_source=50)
    return [(feed.__dict__, len(payload)) for feed, payload in results]


def parse_articles(raw_feed_payloads: List[Tuple[FeedSource, bytes]]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    for feed, payload in raw_feed_payloads:
        parsed.extend(news_ingestor.parse_articles(feed, payload, limit_per_source=50))
    return parsed


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return news_ingestor.deduplicate_articles(articles)


def normalize_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return news_ingestor.normalize_articles(articles)


async def store_in_neo4j(articles: List[Dict[str, Any]]) -> int:
    return await news_ingestor.store_in_neo4j(articles)


async def _run_interval(minutes: int, limit_per_source: int, category: Optional[str]) -> None:
    interval_seconds = max(1, minutes) * 60
    while True:
        await news_ingestor.ingest_all(limit_per_source=limit_per_source, category=category)
        await asyncio.sleep(interval_seconds)


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return

    level_name = os.getenv("NEWS_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Async news ingestion pipeline")
    parser.add_argument("--limit", type=int, default=50, help="Max articles per source")
    parser.add_argument("--category", type=str, default=None, help="Optional feed category filter")
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=0,
        help="If > 0, run continuously every X minutes",
    )
    return parser


def main() -> None:
    _configure_logging()
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.interval_minutes and args.interval_minutes > 0:
        asyncio.run(_run_interval(args.interval_minutes, args.limit, args.category))
    else:
        asyncio.run(news_ingestor.ingest_all(limit_per_source=args.limit, category=args.category))


if __name__ == "__main__":
    main()
