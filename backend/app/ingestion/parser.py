from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser
from dateutil import parser as date_parser


class NewsParser:
    """Convert RSS/API payloads into a shared raw article schema."""

    def parse_rss_payload(
        self,
        feed_name: str,
        feed_category: str,
        payload: bytes,
        limit_per_source: int,
    ) -> List[Dict[str, Any]]:
        parsed = feedparser.parse(payload)
        entries = list(parsed.entries or [])[: max(1, limit_per_source)]

        articles: List[Dict[str, Any]] = []
        for entry in entries:
            title = self._clean_text(str(getattr(entry, "title", "")).strip())
            url = str(getattr(entry, "link", "")).strip()
            if not title or not url:
                continue
            articles.append(
                {
                    "title": title,
                    "summary": self._clean_text(
                        str(getattr(entry, "summary", "") or getattr(entry, "description", "")).strip()
                    ),
                    "source": feed_name,
                    "published_at": self._to_iso8601(getattr(entry, "published", None)),
                    "url": url,
                    "category": feed_category or "general",
                }
            )
        return articles

    def parse_newsapi_payload(self, payload: Dict[str, Any], category: Optional[str]) -> List[Dict[str, Any]]:
        rows = payload.get("articles", []) if isinstance(payload, dict) else []
        parsed: List[Dict[str, Any]] = []
        for row in rows:
            title = self._clean_text(str(row.get("title") or ""))
            url = str(row.get("url") or "").strip()
            if not title or not url:
                continue
            parsed.append(
                {
                    "title": title,
                    "summary": self._clean_text(str(row.get("description") or row.get("content") or "")),
                    "source": str((row.get("source") or {}).get("name") or "NewsAPI").strip(),
                    "published_at": self._to_iso8601(row.get("publishedAt")),
                    "url": url,
                    "category": (category or "general").lower(),
                }
            )
        return parsed

    def parse_gnews_payload(self, payload: Dict[str, Any], category: Optional[str]) -> List[Dict[str, Any]]:
        rows = payload.get("articles", []) if isinstance(payload, dict) else []
        parsed: List[Dict[str, Any]] = []
        for row in rows:
            title = self._clean_text(str(row.get("title") or ""))
            url = str(row.get("url") or "").strip()
            if not title or not url:
                continue
            parsed.append(
                {
                    "title": title,
                    "summary": self._clean_text(str(row.get("description") or row.get("content") or "")),
                    "source": str((row.get("source") or {}).get("name") or "GNews").strip(),
                    "published_at": self._to_iso8601(row.get("publishedAt")),
                    "url": url,
                    "category": (category or "general").lower(),
                }
            )
        return parsed

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
