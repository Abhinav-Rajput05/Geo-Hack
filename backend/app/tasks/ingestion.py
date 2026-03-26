"""
News Ingestion Tasks
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from asgiref.sync import async_to_sync

from app.tasks.celery_app import celery_app
from app.realtime.ingestion_pipeline import realtime_ingestion_pipeline


@celery_app.task(name='app.tasks.ingestion.ingest_news')
def ingest_news(
    limit: int = 50,
    keywords: Optional[List[str]] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest news from multi-source providers into graph.
    """
    logger.info(f"Celery ingestion task started (limit={limit})")
    try:
        # Use async_to_sync instead of asyncio.run() to properly handle async code
        # from a synchronous Celery task without event loop conflicts
        result = async_to_sync(realtime_ingestion_pipeline.run_once)(
            limit_per_source=limit,
            category=category,
        )
        logger.info(
            "Celery ingestion task completed: "
            f"unique_articles={result.get('unique_articles', 0)}, "
            f"persisted_to_neo4j={result.get('persisted_to_neo4j', 0)}"
        )
        return {
            "status": "completed",
            "articles_ingested": result.get("unique_articles", 0),
            "persisted_to_neo4j": result.get("persisted_to_neo4j", 0),
            "sources": result.get("sources", []),
            "source_counts": result.get("source_counts", {}),
            "dedup_metrics": result.get("dedup_metrics", {}),
            "processing_seconds": result.get("processing_seconds", 0),
            "ingested_at": result.get("ingested_at"),
        }
    except Exception as e:
        logger.error(f"Celery ingestion task failed: {e}")
        return {
            "status": "error",
            "articles_ingested": 0,
            "persisted_to_neo4j": 0,
            "error": str(e),
        }


@celery_app.task(name='app.tasks.ingestion.fetch_article_content')
def fetch_article_content(article_id: str, url: str) -> Dict[str, Any]:
    """
    Fetch full content from article URL
    """
    # Stub for compatibility; raw text is currently extracted in ingestion pipeline.
    return {"article_id": article_id, "url": url, "status": "not_implemented"}


@celery_app.task(name='app.tasks.ingestion.clean_duplicate_articles')
def clean_duplicate_articles() -> Dict[str, Any]:
    """
    Remove duplicate articles based on URL or content hash
    """
    # Duplicate handling is performed in-stream by NewsDeduplicator.
    return {"status": "completed", "message": "In-stream deduplication is active"}
