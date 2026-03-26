from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.ingestion.deduplicator import NewsDeduplicator
from app.ingestion.entity_extractor import NewsEntityExtractor
from app.ingestion.news_ingestor import news_ingestor
from app.ingestion.parser import NewsParser
from app.ingestion.sources.api_sources import APISourcesClient
from app.ingestion.sources.rss_sources import RSSFeedSource, RSSSourcesClient

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """RSS-first ingestion with API fallback, dedup, enrichment, and Neo4j persistence."""

    def __init__(self) -> None:
        self.news_ingestor = news_ingestor
        self.parser = NewsParser()
        self.deduplicator = NewsDeduplicator(
            similarity_threshold=float(getattr(settings, "NEWS_DEDUP_SIMILARITY_THRESHOLD", 0.86)),
            duplicate_ttl_seconds=int(getattr(settings, "NEWS_DEDUP_TTL_SECONDS", 6 * 60 * 60)),
        )
        self.entity_extractor = NewsEntityExtractor(
            max_raw_text_chars=int(getattr(settings, "NEWS_MAX_RAW_TEXT_CHARS", 9000)),
            max_llm_text_chars=int(getattr(settings, "NEWS_MAX_LLM_TEXT_CHARS", 2800)),
            use_llm_enrichment=bool(getattr(settings, "NEWS_USE_LLM_ENRICHMENT", False)),
        )
        self.rss_client = RSSSourcesClient(
            timeout_seconds=self.news_ingestor.fetch_timeout_seconds,
            max_concurrent_fetches=self.news_ingestor.max_concurrent_fetches,
            retries=self.news_ingestor.fetch_retries,
        )
        self.api_client = APISourcesClient(
            newsapi_key=self.news_ingestor.newsapi_key,
            gnews_key=getattr(settings, "GNEWS_API_KEY", None),
            timeout_seconds=self.news_ingestor.fetch_timeout_seconds,
            max_concurrent_fetches=max(2, self.news_ingestor.max_concurrent_fetches // 2),
        )
        self.max_enrichment_concurrency = int(getattr(settings, "NEWS_MAX_CONCURRENT_ENRICHMENT", 4))
        self._enrichment_semaphore = asyncio.Semaphore(max(1, self.max_enrichment_concurrency))

    async def run_once(
        self,
        limit_per_source: int = 50,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        source_failures: Dict[str, str] = {}

        try:
            feeds = self.news_ingestor.load_feeds(category=category)
            rss_feeds = [RSSFeedSource(name=f.name, url=f.url, category=f.category) for f in feeds]

            rss_payloads, rss_failures = await self.rss_client.fetch_all(rss_feeds)
            source_failures.update(rss_failures)

            rss_articles: List[Dict[str, Any]] = []
            for feed, payload in rss_payloads:
                parsed = self.parser.parse_rss_payload(feed.name, feed.category, payload, limit_per_source)
                rss_articles.extend(parsed)
                logger.info("[INFO] RSS fetched: %s -> %s articles", feed.name, len(parsed))

            api_articles: List[Dict[str, Any]] = []
            min_required = max(10, min(35, limit_per_source))
            use_api_fallback = len(rss_articles) < min_required

            if use_api_fallback:
                newsapi_rows, newsapi_error = await self.api_client.fetch_newsapi(limit_per_source, category)
                if newsapi_error:
                    source_failures["NewsAPI"] = newsapi_error
                api_articles.extend(newsapi_rows)

                if len(api_articles) < min_required:
                    gnews_rows, gnews_error = await self.api_client.fetch_gnews(limit_per_source, category)
                    if gnews_error:
                        source_failures["GNews"] = gnews_error
                    api_articles.extend(gnews_rows)

            merged_articles = rss_articles + api_articles
            unique_articles, dedup_metrics = await self.deduplicator.deduplicate(merged_articles)
            logger.info("[INFO] Deduplicated: %s removed", dedup_metrics.get("removed_total", 0))

            for article in unique_articles:
                article["id"] = self._build_article_hash(article.get("title", ""), article.get("url", ""))

            normalized_articles = self.news_ingestor.normalize_articles(unique_articles)
            enriched_articles = await self._enrich_articles(normalized_articles)

            stored_count = await self.news_ingestor.store_in_neo4j(enriched_articles)
            source_counts = self._count_by_source(enriched_articles)

            duration_sec = round((datetime.now(timezone.utc) - started_at).total_seconds(), 3)
            return {
                "total_feeds_processed": len(feeds),
                "total_articles": len(merged_articles),
                "total_articles_fetched": len(merged_articles),
                "unique_articles": len(enriched_articles),
                "persisted_to_neo4j": stored_count,
                "source_failures": source_failures,
                "source_counts": source_counts,
                "sources": sorted(source_counts.keys()),
                "dedup_metrics": dedup_metrics,
                "processing_seconds": duration_sec,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "articles": enriched_articles,
                "published_events": 0,
            }
        except Exception as exc:
            logger.error("[ERROR] Ingestion pipeline failed: %s", exc)
            return {
                "total_feeds_processed": 0,
                "total_articles": 0,
                "total_articles_fetched": 0,
                "unique_articles": 0,
                "persisted_to_neo4j": 0,
                "source_failures": {"pipeline": str(exc), **source_failures},
                "source_counts": {},
                "sources": [],
                "dedup_metrics": {"input_count": 0, "output_count": 0, "removed_total": 0},
                "processing_seconds": 0,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "articles": [],
                "published_events": 0,
            }

    async def _enrich_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tasks = [asyncio.create_task(self._enrich_one(article)) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[Dict[str, Any]] = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("[WARN] Article enrichment failed, using normalized article: %s", result)
                enriched.append(articles[idx])
            else:
                enriched.append(result)
        return enriched

    async def _enrich_one(self, article: Dict[str, Any]) -> Dict[str, Any]:
        async with self._enrichment_semaphore:
            try:
                enriched = await self.entity_extractor.enrich_article(article)
                if not enriched.get("categories"):
                    category = enriched.get("category")
                    enriched["categories"] = [category] if category else []
                return enriched
            except Exception as exc:
                logger.warning("[WARN] Enrichment error: %s", exc)
                return article

    @staticmethod
    def _count_by_source(articles: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for article in articles:
            source = article.get("source", "Unknown")
            counts[source] = counts.get(source, 0) + 1
        return counts

    @staticmethod
    def _build_article_hash(title: str, url: str) -> str:
        payload = f"{title.strip().lower()}::{url.strip().lower()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


ingestion_pipeline = IngestionPipeline()
