from __future__ import annotations

import asyncio
import json
import logging

from app.config import settings
from app.database.redis_client import redis_client
from app.realtime.websocket_server import ws_manager

logger = logging.getLogger(__name__)


class RedisEventConsumer:
    """Consumes Redis Pub/Sub article events and broadcasts over WebSocket."""

    def __init__(self) -> None:
        self.channel = str(getattr(settings, "REDIS_NEWS_CHANNEL", "news:articles:live"))

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            pubsub = None
            try:
                if not redis_client.client:
                    await redis_client.connect()

                pubsub = redis_client.client.pubsub(ignore_subscribe_messages=True)
                await pubsub.subscribe(self.channel)
                logger.info("[EVENT] Consumer subscribed on channel: %s", self.channel)

                while not stop_event.is_set():
                    message = await pubsub.get_message(timeout=1.0)
                    if not message:
                        await asyncio.sleep(0.05)
                        continue

                    raw = message.get("data")
                    if not raw:
                        continue

                    event = json.loads(raw)
                    await ws_manager.broadcast(event)
            except Exception as exc:
                logger.error("[ERROR] Redis consumer failure: %s", exc)
                await asyncio.sleep(2.0)
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe(self.channel)
                        await pubsub.close()
                    except Exception:
                        pass


redis_event_consumer = RedisEventConsumer()
