"""
News API Endpoints - Live News Ingestion and Management
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from dateutil import parser as date_parser
from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.database.redis_client import redis_client
from app.realtime.ingestion_pipeline import realtime_ingestion_pipeline
from app.vectorstore import chroma_service
from app.limiter import limiter

router = APIRouter()

NEWS_CACHE_KEY = "news:articles:v1"
NEWS_STATUS_KEY = "news:status:v1"
NEWS_CACHE_TTL_SECONDS = 300


class NewsArticle(BaseModel):
    """News article model"""

    id: str
    title: str
    summary: str
    content: Optional[str] = None
    source: str
    url: str
    published_at: str
    categories: List[str]
    entities: List[Dict[str, Any]]
    sentiment: Optional[str] = None
    relevance_score: Optional[float] = None


class IngestionStatus(BaseModel):
    """Ingestion status model"""

    last_run: Optional[str]
    next_run: Optional[str]
    articles_ingested: int
    sources_active: int
    status: str  # running, idle, error


class NewsSource(BaseModel):
    """News source model"""

    name: str
    type: str  # rss, api, scraper
    url: str
    active: bool
    last_fetch: Optional[str]
    articles_count: int


@router.get("/articles", response_model=List[NewsArticle])
async def get_articles(
    limit: int = 20,
    offset: int = 0,
    source: Optional[str] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
    domain: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """
    Get ingested news articles with filters
    """
    articles = await _load_or_refresh_articles()
    filtered = _apply_filters(
        articles=articles,
        source=source,
        category=category,
        region=region,
        domain=domain,
        from_date=from_date,
        to_date=to_date,
    )
    sliced = filtered[max(offset, 0): max(offset, 0) + max(limit, 0)]
    return [_to_news_article(item) for item in sliced]


@router.get("/ingestion/status", response_model=IngestionStatus)
async def get_ingestion_status():
    """
    Get current news ingestion status
    """
    status = await redis_client.get(NEWS_STATUS_KEY) or {}
    last_run = status.get("last_run")
    sources_active = (
        len(settings.rss_feeds)
        + (1 if settings.news_api_key else 0)
        + (1 if settings.GNEWS_API_KEY else 0)
        + (1 if settings.GDELT_ENABLED else 0)
        + (1 if settings.EVENT_REGISTRY_API_KEY else 0)
    )
    total = status.get("articles_ingested", 0)
    next_run = None
    if last_run:
        parsed_last = _parse_datetime(last_run)
        if parsed_last:
            next_run = (
                parsed_last
                .replace(microsecond=0)
                .timestamp()
                + (settings.INGESTION_INTERVAL_MINUTES * 60)
            )
            next_run = datetime.utcfromtimestamp(next_run).isoformat()

    return IngestionStatus(
        last_run=last_run,
        next_run=next_run,
        articles_ingested=total,
        sources_active=sources_active,
        status=status.get("status", "idle"),
    )


@router.post("/ingestion/trigger")
@limiter.limit("5/minute")  # Rate limit expensive ingestion triggers
async def trigger_ingestion(request: Request):
    """
    Manually trigger news ingestion
    """
    try:
        logger.info("Manual ingestion trigger requested via /ingestion/trigger")
        result = await _refresh_articles()
    except Exception as e:
        logger.error(f"Manual ingestion trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}") from e

    return {
        "message": "Ingestion triggered successfully",
        "task_id": f"ingest-{uuid4()}",
        "articles_ingested": result.get("unique_articles", 0),
    }


@router.post("/trigger-ingestion")
@limiter.limit("2/minute")  # Rate limit debug endpoint even more strictly
async def trigger_ingestion_debug(
    request: Request,
    limit_per_source: int = 5,
    keywords: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
):
    """
    Debug endpoint to manually run ingestion with a small limit.
    """
    logger.info(
        f"Manual debug ingestion trigger requested via /trigger-ingestion "
        f"(limit_per_source={limit_per_source})"
    )
    try:
        _ = keywords, country  # Reserved for compatibility.
        result = await realtime_ingestion_pipeline.run_once(
            limit_per_source=limit_per_source,
            category=category,
        )
        return {
            "message": "Debug ingestion completed",
            "limit_per_source": limit_per_source,
            "total_articles": result.get("total_articles", 0),
            "unique_articles": result.get("unique_articles", 0),
            "persisted_to_neo4j": result.get("persisted_to_neo4j", 0),
            "sources": result.get("sources", []),
            "source_counts": result.get("source_counts", {}),
            "dedup_metrics": result.get("dedup_metrics", {}),
            "source_failures": result.get("source_failures", {}),
        }
    except Exception as e:
        logger.error(f"Debug ingestion trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Debug ingestion failed: {e}") from e


@router.get("/sources", response_model=List[NewsSource])
async def get_sources():
    """
    Get all configured news sources
    """
    articles = await redis_client.get(NEWS_CACHE_KEY) or []
    source_counts: Dict[str, int] = {}
    for article in articles:
        source_name = article.get("source", "Unknown")
        source_counts[source_name] = source_counts.get(source_name, 0) + 1

    sources = []
    for url in settings.rss_feeds:
        host = _host_from_url(url)
        count = source_counts.get(host, 0)
        if count == 0:
            count = sum(v for k, v in source_counts.items() if host in k.lower())
        sources.append(
            NewsSource(
                name=host,
                type="rss",
                url=url,
                active=True,
                last_fetch=None,
                articles_count=count,
            )
        )

    if settings.news_api_key:
        sources.append(
            NewsSource(
                name="NewsAPI",
                type="api",
                url="https://newsapi.org/v2/top-headlines",
                active=True,
                last_fetch=None,
                articles_count=source_counts.get("NewsAPI", 0),
            )
        )

    if settings.GNEWS_API_KEY:
        sources.append(
            NewsSource(
                name="GNews",
                type="api",
                url=settings.GNEWS_BASE_URL,
                active=True,
                last_fetch=None,
                articles_count=source_counts.get("GNews", 0),
            )
        )

    if settings.GDELT_ENABLED:
        sources.append(
            NewsSource(
                name="GDELT",
                type="osint",
                url="https://api.gdeltproject.org/api/v2/doc/doc",
                active=True,
                last_fetch=None,
                articles_count=source_counts.get("GDELT", 0),
            )
        )

    if settings.EVENT_REGISTRY_API_KEY:
        sources.append(
            NewsSource(
                name="EventRegistry",
                type="api",
                url="https://eventregistry.org/api/v1/article/getArticles",
                active=True,
                last_fetch=None,
                articles_count=source_counts.get("EventRegistry", 0),
            )
        )

    return sources


@router.post("/sources")
async def add_source(source: NewsSource):
    """
    Add a new news source
    """
    return {
        "message": "Source added successfully",
        "source": source,
    }


@router.delete("/sources/{source_id}")
async def remove_source(source_id: str):
    """
    Remove a news source
    """
    return {
        "message": f"Source {source_id} removed successfully",
    }


@router.get("/stats")
async def get_news_stats():
    """
    Get news ingestion statistics
    """
    articles = await _load_or_refresh_articles()
    now = datetime.utcnow()

    by_category: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    today_count = 0
    week_count = 0
    one_week_ago = now.timestamp() - (7 * 24 * 60 * 60)

    for article in articles:
        for cat in article.get("categories", []):
            by_category[cat] = by_category.get(cat, 0) + 1
        source_name = article.get("source", "Unknown")
        by_source[source_name] = by_source.get(source_name, 0) + 1

        published = _parse_datetime(article.get("published_at"))
        if published:
            if published.date() == now.date():
                today_count += 1
            if published.timestamp() >= one_week_ago:
                week_count += 1

    return {
        "total_articles": len(articles),
        "articles_today": today_count,
        "articles_this_week": week_count,
        "by_category": by_category,
        "by_source": by_source,
        "processing_queue": 0,
        "processed_today": today_count,
    }


async def _load_or_refresh_articles() -> List[Dict[str, Any]]:
    cached = await redis_client.get(NEWS_CACHE_KEY)
    if isinstance(cached, list) and cached:
        return cached

    result = await _refresh_articles()
    return result.get("articles", [])


async def _refresh_articles() -> Dict[str, Any]:
    logger.info("News refresh started")
    await redis_client.set(
        NEWS_STATUS_KEY,
        {"status": "running", "last_run": datetime.utcnow().isoformat(), "articles_ingested": 0},
        expire=NEWS_CACHE_TTL_SECONDS,
    )
    ingestion = await realtime_ingestion_pipeline.run_once(limit_per_source=30)
    normalized = [_normalize_article(article) for article in ingestion.get("articles", [])]
    logger.info(
        "News refresh fetched "
        f"{ingestion.get('unique_articles', 0)} unique articles "
        f"and persisted {ingestion.get('persisted_to_neo4j', 0)} to Neo4j"
    )

    await redis_client.set(NEWS_CACHE_KEY, normalized, expire=NEWS_CACHE_TTL_SECONDS)
    await redis_client.set(
        NEWS_STATUS_KEY,
        {
            "status": "idle",
            "last_run": datetime.utcnow().isoformat(),
            "articles_ingested": len(normalized),
        },
        expire=NEWS_CACHE_TTL_SECONDS,
    )

    try:
        texts = [
            f"{item.get('title', '')}\n{item.get('summary', '')}\n{item.get('content', '')}"
            for item in normalized
        ]
        metadatas = [
            {"source": item.get("source", "news"), "url": item.get("url", "")}
            for item in normalized
        ]
        await chroma_service.add_documents(texts, metadatas)
    except Exception:
        pass

    ingestion["articles"] = normalized
    logger.info("News refresh completed")
    return ingestion


def _normalize_article(article: Dict[str, Any]) -> Dict[str, Any]:
    title = article.get("title", "Untitled")
    summary = article.get("summary", "")
    content = article.get("content")
    region = article.get("region") or _infer_region(title, summary)
    categories = article.get("categories", [])
    if not categories and article.get("category"):
        categories = [str(article.get("category"))]

    return {
        "id": article.get("id") or str(uuid4()),
        "title": title,
        "summary": summary,
        "content": content,
        "source": article.get("source", "Unknown"),
        "url": article.get("url", ""),
        "published_at": article.get("published_at") or datetime.utcnow().isoformat(),
        "categories": categories,
        "domain": article.get("domain") or article.get("topic") or (categories[0] if categories else "General"),
        "region": region or (article.get("location", {}) or {}).get("name", "Global"),
        "location": article.get("location") or {"name": region or "Global"},
        "entities": article.get("entities", []),
        "sentiment": article.get("sentiment"),
        "relevance_score": article.get("relevance_score") or article.get("confidence_score"),
        "source_credibility": article.get("source_credibility"),
        "event_key": article.get("event_key"),
    }


def _to_news_article(article: Dict[str, Any]) -> NewsArticle:
    return NewsArticle(
        id=str(article.get("id", uuid4())),
        title=article.get("title", "Untitled"),
        summary=article.get("summary", ""),
        content=article.get("content"),
        source=article.get("source", "Unknown"),
        url=article.get("url", ""),
        published_at=article.get("published_at", datetime.utcnow().isoformat()),
        categories=article.get("categories", []),
        entities=article.get("entities", []),
        sentiment=article.get("sentiment"),
        relevance_score=article.get("relevance_score"),
    )


def _apply_filters(
    articles: List[Dict[str, Any]],
    source: Optional[str],
    category: Optional[str],
    region: Optional[str],
    domain: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
) -> List[Dict[str, Any]]:
    filtered = articles

    if source:
        filtered = [a for a in filtered if a.get("source", "").lower() == source.lower()]
    if category:
        filtered = [
            a for a in filtered
            if any(category.lower() == str(cat).lower() for cat in a.get("categories", []))
        ]
    if domain:
        filtered = [
            a for a in filtered
            if domain.lower() == str(a.get("domain", "")).lower()
            or any(domain.lower() == str(cat).lower() for cat in a.get("categories", []))
        ]
    if region:
        filtered = [a for a in filtered if str(a.get("region", "")).lower() == region.lower()]

    from_dt = _parse_datetime(from_date) if from_date else None
    to_dt = _parse_datetime(to_date) if to_date else None
    if from_dt or to_dt:
        tmp = []
        for article in filtered:
            published = _parse_datetime(article.get("published_at"))
            if not published:
                continue
            if from_dt and published < from_dt:
                continue
            if to_dt and published > to_dt:
                continue
            tmp.append(article)
        filtered = tmp

    filtered.sort(
        key=lambda x: _parse_datetime(x.get("published_at")) or datetime.min,
        reverse=True,
    )
    return filtered


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def _infer_region(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    mapping = {
        "North America": ["united states", "canada", "mexico", "washington"],
        "Europe": ["europe", "ukraine", "russia", "germany", "france", "uk"],
        "Asia Pacific": ["china", "india", "japan", "korea", "taiwan", "asia"],
        "Middle East": ["iran", "israel", "saudi", "qatar", "middle east"],
        "Africa": ["africa", "nigeria", "egypt", "ethiopia", "south africa"],
        "South America": ["brazil", "argentina", "chile", "peru", "colombia"],
    }
    for region, keywords in mapping.items():
        if any(keyword in text for keyword in keywords):
            return region
    return "Global"


def _host_from_url(url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(url).netloc.lower().replace("www.", "")
    return host or url
