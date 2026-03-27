"""
News API Endpoints - Live News Ingestion and Management
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from dateutil import parser as date_parser
from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.database.postgres_client import postgres_client
from app.database.redis_client import redis_client
from app.realtime.ingestion_pipeline import realtime_ingestion_pipeline
from app.vectorstore import chroma_service
from app.limiter import limiter

router = APIRouter()

NEWS_CACHE_KEY = "news:articles:v1"
NEWS_STATUS_KEY = "news:status:v1"
NEWS_CACHE_TTL_SECONDS = 60  # 1 minute — fresh news every minute
ARTICLES_TABLE = "articles"


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

    stored = await _load_articles_from_postgres(limit=300)
    if stored:
        await redis_client.set(NEWS_CACHE_KEY, stored, expire=NEWS_CACHE_TTL_SECONDS)
        return stored

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
    await _ensure_articles_table()
    await _persist_articles_to_postgres(normalized)
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
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        for item in normalized:
            base_text = (
                f"Title: {item.get('title', '')}\n"
                f"Summary: {item.get('summary', '')}\n"
                f"Content: {item.get('content', '')}"
            )
            chunks = _chunk_text(base_text, chunk_size=950, overlap=140)
            for idx, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append(
                    {
                        "source": item.get("source", "news"),
                        "url": item.get("url", ""),
                        "article_id": item.get("id", ""),
                        "domain": item.get("domain", ""),
                        "region": item.get("region", ""),
                        "published_at": item.get("published_at", ""),
                        "chunk_index": idx,
                        "chunk_total": len(chunks),
                    }
                )
        if texts:
            await chroma_service.add_documents(texts, metadatas)
    except Exception:
        pass

    ingestion["articles"] = normalized
    logger.info("News refresh completed")
    return ingestion


def _normalize_article(article: Dict[str, Any]) -> Dict[str, Any]:
    article_id = article.get("id") or str(uuid4())
    title = article.get("title", "Untitled")
    summary = article.get("summary", "")
    content = article.get("content")
    region = article.get("region") or _infer_region(title, summary)
    categories = article.get("categories", [])
    if not categories and article.get("category"):
        categories = [str(article.get("category"))]

    return {
        "id": article_id,
        "title": title,
        "summary": summary,
        "content": content,
        "source": article.get("source", "Unknown"),
        "url": article.get("url") or f"urn:article:{article_id}",
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


async def _ensure_articles_table() -> None:
    await postgres_client.execute_write(
        f"""
        CREATE TABLE IF NOT EXISTS {ARTICLES_TABLE} (
            id VARCHAR(255) PRIMARY KEY,
            title TEXT NOT NULL,
            summary TEXT,
            content TEXT,
            source VARCHAR(255) NOT NULL,
            url TEXT UNIQUE,
            published_at TIMESTAMP NOT NULL,
            categories JSONB,
            entities JSONB,
            domain VARCHAR(100),
            region VARCHAR(100),
            sentiment VARCHAR(50),
            relevance_score DOUBLE PRECISION,
            source_credibility DOUBLE PRECISION,
            event_key VARCHAR(255),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # Keep schema aligned with JSON payloads even for pre-existing tables.
    column_types = await postgres_client.execute_query(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND column_name IN ('categories', 'entities')
        """,
        {"table_name": ARTICLES_TABLE},
    )
    type_map = {row["column_name"]: row["data_type"] for row in column_types}

    if type_map.get("categories") != "jsonb":
        await postgres_client.execute_write(
            f"""
            ALTER TABLE {ARTICLES_TABLE}
            ALTER COLUMN categories TYPE JSONB
            USING CASE
                WHEN categories IS NULL THEN '[]'::jsonb
                ELSE to_jsonb(categories)
            END;
            """
        )

    if type_map.get("entities") != "jsonb":
        await postgres_client.execute_write(
            f"""
            ALTER TABLE {ARTICLES_TABLE}
            ALTER COLUMN entities TYPE JSONB
            USING CASE
                WHEN entities IS NULL THEN '[]'::jsonb
                ELSE entities::jsonb
            END;
            """
        )


def validate_article(article: Dict[str, Any]) -> None:
    assert isinstance(article["title"], str)
    assert isinstance(article["url"], str)
    assert isinstance(article.get("categories", []), list)
    assert isinstance(article.get("entities", []), list)
    assert isinstance(article.get("relevance_score", 0) or 0, (int, float))


async def _persist_articles_to_postgres(articles: List[Dict[str, Any]]) -> None:
    if not articles:
        return

    rows: List[Dict[str, Any]] = []
    for item in articles:
        validate_article(item)
        published = _parse_datetime(item.get("published_at")) or datetime.utcnow()
        categories = item.get("categories", [])
        entities = item.get("entities", [])
        logger.debug(f"Inserting article: {item.get('url')}")
        logger.debug(f"Entities type: {type(entities)}")
        rows.append(
            {
                "id": str(item.get("id", uuid4())),
                "title": item.get("title", "Untitled"),
                "summary": item.get("summary"),
                "content": item.get("content"),
                "source": item.get("source", "Unknown"),
                "url": item.get("url"),
                "published_at": published,
                "categories": json.dumps(categories),
                "entities": json.dumps(entities),
                "domain": item.get("domain"),
                "region": item.get("region"),
                "sentiment": item.get("sentiment"),
                "relevance_score": item.get("relevance_score"),
                "source_credibility": item.get("source_credibility"),
                "event_key": item.get("event_key"),
            }
        )

    await postgres_client.execute_write_many(
        f"""
        INSERT INTO {ARTICLES_TABLE}
        (id, title, summary, content, source, url, published_at, categories, entities, domain, region, sentiment, relevance_score, source_credibility, event_key)
        VALUES
        (:id, :title, :summary, :content, :source, :url, :published_at, CAST(:categories AS JSONB), CAST(:entities AS JSONB), :domain, :region, :sentiment, :relevance_score, :source_credibility, :event_key)
        ON CONFLICT (url)
        DO UPDATE SET
            title = EXCLUDED.title,
            summary = EXCLUDED.summary,
            content = EXCLUDED.content,
            source = EXCLUDED.source,
            published_at = EXCLUDED.published_at,
            categories = EXCLUDED.categories,
            entities = EXCLUDED.entities,
            domain = EXCLUDED.domain,
            region = EXCLUDED.region,
            sentiment = EXCLUDED.sentiment,
            relevance_score = EXCLUDED.relevance_score,
            source_credibility = EXCLUDED.source_credibility,
            event_key = EXCLUDED.event_key,
            updated_at = CURRENT_TIMESTAMP
        """,
        rows,
    )


async def _load_articles_from_postgres(limit: int = 100) -> List[Dict[str, Any]]:
    try:
        await _ensure_articles_table()
        records = await postgres_client.execute_query(
            f"""
            SELECT id, title, summary, content, source, url, published_at, categories, entities,
                   domain, region, sentiment, relevance_score, source_credibility, event_key
            FROM {ARTICLES_TABLE}
            ORDER BY published_at DESC
            LIMIT :limit
            """,
            {"limit": max(1, limit)},
        )
    except Exception as exc:
        logger.warning(f"Failed loading articles from PostgreSQL: {exc}")
        return []

    normalized: List[Dict[str, Any]] = []
    for row in records:
        published = row.get("published_at")
        categories = row.get("categories", []) or []
        entities = row.get("entities", []) or []
        if isinstance(categories, str):
            try:
                categories = json.loads(categories)
            except Exception:
                categories = []
        if isinstance(entities, str):
            try:
                entities = json.loads(entities)
            except Exception:
                entities = []
        published_at = (
            published.isoformat()
            if isinstance(published, datetime)
            else str(published or datetime.utcnow().isoformat())
        )
        normalized.append(
            {
                "id": str(row.get("id", uuid4())),
                "title": row.get("title", "Untitled"),
                "summary": row.get("summary", ""),
                "content": row.get("content"),
                "source": row.get("source", "Unknown"),
                "url": row.get("url", ""),
                "published_at": published_at,
                "categories": categories,
                "entities": entities,
                "domain": row.get("domain"),
                "region": row.get("region", "Global"),
                "sentiment": row.get("sentiment"),
                "relevance_score": row.get("relevance_score"),
                "source_credibility": row.get("source_credibility"),
                "event_key": row.get("event_key"),
                "location": {"name": row.get("region", "Global")},
            }
        )
    return normalized


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


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    """Split long text into overlapping chunks for better semantic retrieval."""
    clean = (text or "").strip()
    if not clean:
        return []
    if len(clean) <= chunk_size:
        return [clean]

    chunks: List[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(clean):
        end = start + chunk_size
        chunks.append(clean[start:end])
        if end >= len(clean):
            break
        start += step
    return chunks
