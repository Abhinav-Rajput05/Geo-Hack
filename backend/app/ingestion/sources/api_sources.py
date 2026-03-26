from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ingestion.parser import NewsParser

logger = logging.getLogger(__name__)


class APISourcesClient:
    """Fetch API-based news sources with graceful failure handling."""

    def __init__(
        self,
        newsapi_key: Optional[str],
        gnews_key: Optional[str],
        timeout_seconds: int = 8,
        max_concurrent_fetches: int = 4,
    ) -> None:
        self.newsapi_key = newsapi_key
        self.gnews_key = gnews_key
        self.timeout_seconds = timeout_seconds
        self.max_concurrent_fetches = max_concurrent_fetches
        self._semaphore = asyncio.Semaphore(max_concurrent_fetches)
        self.parser = NewsParser()

    async def fetch_newsapi(
        self,
        limit_per_source: int,
        category: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not self.newsapi_key:
            return [], "NEWS_API_KEY not configured"

        endpoint = "https://newsapi.org/v2/top-headlines"
        params: Dict[str, Any] = {
            "apiKey": self.newsapi_key,
            "language": "en",
            "pageSize": max(1, min(limit_per_source, 100)),
        }
        if category:
            params["category"] = category.lower()

        try:
            payload = await self._request_json(endpoint, params=params, source_name="NewsAPI")
            parsed = self.parser.parse_newsapi_payload(payload, category=category)
            logger.info("[INFO] API fetched: NewsAPI -> %s articles", len(parsed))
            return parsed, None
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else "unknown"
            # 401 must be graceful and non-fatal.
            error = f"{status_code} Unauthorized" if status_code == 401 else f"HTTP {status_code}"
            logger.error("[ERROR] NewsAPI failed: %s", error)
            return [], error
        except Exception as exc:
            logger.error("[ERROR] NewsAPI failed: %s", exc)
            return [], str(exc)

    async def fetch_gnews(
        self,
        limit_per_source: int,
        category: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not self.gnews_key:
            return [], "GNEWS_API_KEY not configured"

        endpoint = "https://gnews.io/api/v4/top-headlines"
        params: Dict[str, Any] = {
            "token": self.gnews_key,
            "lang": "en",
            "max": max(1, min(limit_per_source, 100)),
        }
        if category:
            params["topic"] = category.lower()

        try:
            payload = await self._request_json(endpoint, params=params, source_name="GNews")
            parsed = self.parser.parse_gnews_payload(payload, category=category)
            logger.info("[INFO] API fetched: GNews -> %s articles", len(parsed))
            return parsed, None
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else "unknown"
            error = f"HTTP {status_code}"
            logger.error("[ERROR] GNews failed: %s", error)
            return [], error
        except Exception as exc:
            logger.error("[ERROR] GNews failed: %s", exc)
            return [], str(exc)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.7, min=0.7, max=4.5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def _request_json(self, url: str, params: Dict[str, Any], source_name: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout_seconds)
        limits = httpx.Limits(max_connections=self.max_concurrent_fetches, max_keepalive_connections=10)
        headers = {"User-Agent": "global-ontology-engine/4.0"}

        async with self._semaphore:
            async with httpx.AsyncClient(timeout=timeout, limits=limits, headers=headers, follow_redirects=True) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                logger.info("[INFO] API success: %s", source_name)
                return data
