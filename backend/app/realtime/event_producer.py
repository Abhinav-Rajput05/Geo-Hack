from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.config import settings
from app.database.redis_client import redis_client

logger = logging.getLogger(__name__)


class RedisEventProducer:
    """Publishes normalized article events into Redis Pub/Sub."""

    def __init__(self) -> None:
        self.channel = str(getattr(settings, "REDIS_NEWS_CHANNEL", "news:articles:live"))

    async def publish_article_event(self, article: Dict[str, Any]) -> bool:
        event = {
            "id": article.get("id", ""),
            "title": article.get("title", ""),
            "summary": article.get("summary", ""),
            "source": article.get("source", "Unknown"),
            "published_at": article.get("published_at", ""),
            "category": article.get("category", "general"),
            "url": article.get("url", ""),
        }

        try:
            if not redis_client.client:
                await redis_client.connect()

            payload = json.dumps(event, ensure_ascii=False)
            await redis_client.client.publish(self.channel, payload)
            logger.info("[EVENT] Published: %s", event.get("title", "Untitled"))
            return True
        except Exception as exc:
            logger.error("[ERROR] Redis connection failed while publishing event: %s", exc)
            return False


redis_event_producer = RedisEventProducer()
