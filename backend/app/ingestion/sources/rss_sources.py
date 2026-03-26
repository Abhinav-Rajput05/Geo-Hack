from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RSSFeedSource:
    name: str
    url: str
    category: str


class RSSSourcesClient:
    """Fetch RSS sources in parallel with retry and bounded concurrency."""

    def __init__(
        self,
        timeout_seconds: int = 8,
        max_concurrent_fetches: int = 8,
        retries: int = 3,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_concurrent_fetches = max_concurrent_fetches
        self.retries = retries
        self._semaphore = asyncio.Semaphore(max_concurrent_fetches)

    async def fetch_all(
        self,
        feeds: List[RSSFeedSource],
    ) -> Tuple[List[Tuple[RSSFeedSource, bytes]], Dict[str, str]]:
        successes: List[Tuple[RSSFeedSource, bytes]] = []
        failures: Dict[str, str] = {}

        timeout = httpx.Timeout(self.timeout_seconds)
        limits = httpx.Limits(max_connections=self.max_concurrent_fetches, max_keepalive_connections=20)
        headers = {"User-Agent": "global-ontology-engine/4.0"}

        async with httpx.AsyncClient(timeout=timeout, limits=limits, headers=headers, follow_redirects=True) as client:
            tasks = [asyncio.create_task(self._fetch_single(client, feed)) for feed in feeds]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                logger.error("[ERROR] RSS fetch task failed unexpectedly: %s", item)
                continue
            feed, payload, error = item
            if error:
                failures[feed.name] = error
                logger.error("[ERROR] RSS failed: %s (%s)", feed.name, error)
                continue
            successes.append((feed, payload))

        return successes, failures

    async def _fetch_single(
        self,
        client: httpx.AsyncClient,
        feed: RSSFeedSource,
    ) -> Tuple[RSSFeedSource, bytes, Optional[str]]:
        try:
            payload = await self._request_with_retry(client, feed.url)
            if not payload:
                raise ValueError("empty response")
            return feed, payload, None
        except Exception as exc:
            return feed, b"", str(exc)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.6, min=0.6, max=4.0),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException, ValueError)),
    )
    async def _request_with_retry(self, client: httpx.AsyncClient, url: str) -> bytes:
        async with self._semaphore:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
