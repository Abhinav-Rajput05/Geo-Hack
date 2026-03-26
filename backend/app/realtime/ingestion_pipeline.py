from __future__ import annotations

from typing import Any, Dict, Optional

from app.ingestion.pipeline import ingestion_pipeline
from app.realtime.event_producer import redis_event_producer


class RealtimeIngestionPipeline:
    """Compatibility wrapper around the modular ingestion pipeline."""

    async def run_once(self, limit_per_source: int = 50, category: Optional[str] = None) -> Dict[str, Any]:
        result = await ingestion_pipeline.run_once(limit_per_source=limit_per_source, category=category)

        published_count = 0
        for article in result.get("articles", []):
            published = await redis_event_producer.publish_article_event(article)
            if published:
                published_count += 1

        result["published_events"] = published_count
        return result


realtime_ingestion_pipeline = RealtimeIngestionPipeline()
