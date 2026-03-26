from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@dataclass(frozen=True)
class ClientSubscription:
    category: Optional[str] = None


class WebSocketManager:
    """Tracks connected clients and broadcasts article events."""

    def __init__(self) -> None:
        self._clients: Dict[WebSocket, ClientSubscription] = {}
        self._lock = asyncio.Lock()
        self._throttle_ms = int(getattr(settings, "WS_EVENT_THROTTLE_MS", 0))
        self._last_broadcast_ts = 0.0

    async def connect(self, websocket: WebSocket, category: Optional[str]) -> None:
        await websocket.accept()
        subscription = ClientSubscription(category=category.lower().strip() if category else None)
        async with self._lock:
            self._clients[websocket] = subscription
        logger.info("[WS] Client connected")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.pop(websocket, None)
        logger.info("[WS] Client disconnected")

    async def broadcast(self, event: Dict) -> None:
        if self._throttle_ms > 0:
            now = asyncio.get_running_loop().time()
            elapsed_ms = (now - self._last_broadcast_ts) * 1000
            if elapsed_ms < self._throttle_ms:
                await asyncio.sleep((self._throttle_ms - elapsed_ms) / 1000)
            self._last_broadcast_ts = asyncio.get_running_loop().time()

        async with self._lock:
            subscribers = list(self._clients.items())

        if not subscribers:
            return

        sent = 0
        tasks = []
        for socket, subscription in subscribers:
            if subscription.category and str(event.get("category", "")).lower() != subscription.category:
                continue
            tasks.append(self._send(socket, event))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if not isinstance(result, Exception) and result:
                    sent += 1

        logger.info("[WS] Broadcast sent to %s clients", sent)

    async def _send(self, websocket: WebSocket, event: Dict) -> bool:
        try:
            await websocket.send_json(event)
            return True
        except Exception:
            await self.disconnect(websocket)
            return False


ws_manager = WebSocketManager()


@ws_router.websocket("/ws/news")
async def news_websocket(websocket: WebSocket, category: Optional[str] = None, token: Optional[str] = None) -> None:
    expected_token = getattr(settings, "WS_AUTH_TOKEN", None)
    if expected_token and token != expected_token:
        await websocket.close(code=1008)
        return

    await ws_manager.connect(websocket, category=category)
    try:
        while True:
            # Keep the socket open. Client can optionally send pings/messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)
