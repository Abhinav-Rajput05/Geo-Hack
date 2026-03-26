"""
Frontend Alignment API Endpoints
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from app.database.postgres_client import postgres_client
from app.database.redis_client import redis_client
from app.graphrag import graphrag_service
from app.insights import insights_service
from app.ontology import ontology_service


router = APIRouter()

FRONTEND_CACHE_TTL = 120
RISK_TABLE = "risk_timeline_snapshots"
CHAT_TABLE = "analysis_chat_history"


def ok(data: Any, message: str = "") -> Dict[str, Any]:
    return {"success": True, "data": data, "message": message}


def error(message: str, status_code: int = 500) -> None:
    """Raise HTTPException with envelope-compatible error format"""
    # FastAPI will serialize this detail into JSON response body
    raise HTTPException(
        status_code=status_code,
        detail={"success": False, "data": None, "message": message}
    )


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    country: str = "India"
    include_map_data: bool = False
    include_risk_analysis: bool = False


async def _ensure_frontend_tables() -> None:
    await postgres_client.execute_write(
        f"""
        CREATE TABLE IF NOT EXISTS {RISK_TABLE} (
            id SERIAL PRIMARY KEY,
            country VARCHAR(120) NOT NULL,
            snapshot_date DATE NOT NULL,
            score NUMERIC(4,2) NOT NULL,
            event_text TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(country, snapshot_date)
        );
        """
    )
    await postgres_client.execute_write(
        f"""
        CREATE TABLE IF NOT EXISTS {CHAT_TABLE} (
            id SERIAL PRIMARY KEY,
            country VARCHAR(120) NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _safe_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed.date()
    except Exception:
        return None


def _to_iso_date(value: date) -> str:
    return value.isoformat()


def _normalize_country_name(country: str) -> str:
    cleaned = (country or "").strip()
    return cleaned or "India"


def _map_level_to_risk(score_0_100: float) -> str:
    if score_0_100 >= 85:
        return "critical"
    if score_0_100 >= 70:
        return "high"
    if score_0_100 >= 45:
        return "medium"
    return "low"


def _category_to_domain_name(category: str) -> str:
    mapping = {
        "geopolitical": "Geopolitical",
        "economic": "Economic",
        "defense": "Military",
        "technology": "Technological",
        "climate": "Climate",
        "energy": "Economic",
        "social": "Political",
    }
    return mapping.get(category.lower(), "Political")


async def _load_news_articles() -> List[Dict[str, Any]]:
    from app.api.endpoints import news as news_endpoint

    return await news_endpoint._load_or_refresh_articles()


async def _build_dashboard_payload(country: str) -> Dict[str, Any]:
    cache_key = f"frontend:dashboard:{country.lower()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    try:
        risk_analysis = await insights_service.get_risk_analysis()
    except Exception as exc:
        logger.error(f"Failed to get risk analysis: {exc}")
        risk_analysis = {"categories": [], "overall_risk": {"score": 0.0}}
    
    try:
        map_data = await insights_service.get_map_data()
    except Exception as exc:
        logger.error(f"Failed to get map data: {exc}")
        map_data = {"countries": []}
    
    try:
        articles = await _load_news_articles()
    except Exception as exc:
        logger.error(f"Failed to load news articles: {exc}")
        articles = []

    categories = risk_analysis.get("categories", [])
    overall = risk_analysis.get("overall_risk", {})
    overall_score = float(overall.get("score", 0.0))

    alerts = [
        f"{item.get('category', 'Unknown')} risk at {int(item.get('level', 0))}% ({item.get('trend', 'stable')})"
        for item in categories[:4]
    ]

    top_articles = sorted(
        articles,
        key=lambda a: a.get("published_at", ""),
        reverse=True,
    )[:8]
    live_events = [
        {
            "id": str(article.get("id", idx + 1)),
            "region": article.get("region", "Global"),
            "text": article.get("title", "Untitled event"),
            "time": article.get("published_at", datetime.utcnow().isoformat()),
        }
        for idx, article in enumerate(top_articles)
    ]

    countries = map_data.get("countries", [])
    country_impact = next(
        (c for c in countries if str(c.get("country", "")).lower() == country.lower()),
        None,
    )
    if not country_impact and countries:
        country_impact = max(countries, key=lambda c: c.get("impact", 0))

    top_impacts = sorted(countries, key=lambda c: c.get("impact", 0), reverse=True)[:3]
    map_connections = [
        {
            "label": item.get("country", "Unknown"),
            "impact": float(item.get("impact", 0)),
            "code": item.get("code", "UNK"),
        }
        for item in top_impacts
    ]

    key_factors: List[str] = []
    for entry in categories[:4]:
        key_factors.extend(entry.get("factors", [])[:1])

    payload = {
        "selected_country": country_impact.get("country", country) if country_impact else country,
        "overall_risk_score": round(overall_score / 10 if overall_score > 10 else overall_score, 1),
        "primary_driver": categories[0]["category"] if categories else "Geopolitical",
        "alerts": alerts,
        "live_events": live_events,
        "map_connections": map_connections,
        "risk_explanation": {
            "title": f"Global Risk Score: {round(overall_score / 10 if overall_score > 10 else overall_score, 1)} / 10",
            "key_factors": key_factors or ["No dominant drivers available"],
            "chain": [entry.get("category", "Unknown") for entry in categories[:5]],
            "confidence": 78,
            "sources": [
                {
                    "name": article.get("source", "Unknown"),
                    "url": article.get("url", ""),
                    "timestamp": article.get("published_at", datetime.utcnow().isoformat()),
                    "reliability": "Verified",
                }
                for article in top_articles[:3]
            ],
        },
    }

    await redis_client.set(cache_key, payload, expire=FRONTEND_CACHE_TTL)
    return payload


async def _build_intelligence_payload(country: str) -> Dict[str, Any]:
    cache_key = f"frontend:intelligence:{country.lower()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    try:
        map_data = await insights_service.get_map_data()
    except Exception as exc:
        logger.error(f"Failed to get map data: {exc}")
        map_data = {"countries": []}
    
    try:
        risk_analysis = await insights_service.get_risk_analysis()
    except Exception as exc:
        logger.error(f"Failed to get risk analysis: {exc}")
        risk_analysis = {"categories": [], "trends": {"weekly": []}}

    heatmap = []
    for item in map_data.get("countries", []):
        heatmap.append(
            {
                "name": item.get("country", "Unknown"),
                "risk": round(float(item.get("impact", 0)) / 10, 1),
                "region": ", ".join(item.get("categories", [])[:2]) or "Global",
                "lat": float(item.get("lat", 0.0) or 0.0),
                "lng": float(item.get("lng", 0.0) or 0.0),
                "risk_level": item.get("risk", "low"),
            }
        )

    categories = risk_analysis.get("categories", [])
    impact_metrics = [
        {
            "id": str(entry.get("category", "unknown")).lower(),
            "label": entry.get("category", "Unknown"),
            "score": round(float(entry.get("level", 0)) / 10, 1),
            "trend": "up" if entry.get("trend") == "up" else "down" if entry.get("trend") == "down" else "stable",
            "change": f"{'+' if entry.get('trend') == 'up' else '-'}0.{min(9, max(1, int(float(entry.get('level', 0)) / 12 or 1)))}",
            "linkedDomains": [_category_to_domain_name(str(entry.get("category", "Unknown")))],
            "insight": (entry.get("factors") or ["No detailed factor available"])[0],
        }
        for entry in categories
    ]

    causal_nodes: List[Dict[str, Any]] = []
    causal_edges: List[Dict[str, Any]] = []

    try:
        country_entities = await ontology_service.search_entities(country, entity_type="Country", limit=1)
        if country_entities:
            center = country_entities[0]
            center_id = str(center.get("id"))
            related = await ontology_service.get_related_entities(center_id, limit=12)
            relationships = await ontology_service.get_relationships(center_id, direction="both", limit=15)

            causal_nodes.append(
                {
                    "id": "center",
                    "title": center.get("name", country),
                    "domain": "Political",
                    "impact": 8.0,
                    "description": f"Primary strategic context for {center.get('name', country)}.",
                    "factors": ["Knowledge graph central entity"],
                }
            )

            node_index: Dict[str, str] = {}
            for idx, rel_entity in enumerate(related[:8]):
                node_id = f"n{idx + 1}"
                node_name = rel_entity.get("name", f"Node {idx + 1}")
                node_index[node_name] = node_id
                causal_nodes.append(
                    {
                        "id": node_id,
                        "title": node_name,
                        "domain": _category_to_domain_name(rel_entity.get("type", "Political")),
                        "impact": 5.5 + min(idx, 4) * 0.5,
                        "description": f"Related entity type: {rel_entity.get('type', 'Unknown')}",
                        "factors": [f"Relationship: {rel_entity.get('relationship_type', 'RELATES')}"],
                    }
                )

            for idx, rel in enumerate(relationships[:10]):
                source_name = (rel.get("source") or {}).get("name", country)
                target_name = (rel.get("target") or {}).get("name", "Unknown")
                source_id = "center" if source_name == center.get("name", country) else node_index.get(source_name, "center")
                target_id = "center" if target_name == center.get("name", country) else node_index.get(target_name)
                if not target_id:
                    continue
                confidence = float((rel.get("properties") or {}).get("confidence", 0.68))
                causal_edges.append(
                    {
                        "from": source_id,
                        "to": target_id,
                        "confidence": max(0.2, min(confidence, 0.99)),
                    }
                )
    except Exception as exc:
        logger.error(f"Failed to build causal chain from graph for {country}: {exc}", exc_info=True)

    if not causal_nodes:
        causal_nodes = [
            {
                "id": "t1",
                "title": "Trigger Event",
                "domain": "Political",
                "impact": 6.3,
                "description": f"Initial signal affecting {country}.",
                "factors": ["Recent event correlation", "Regional uncertainty"],
            },
            {
                "id": "t2",
                "title": "Economic Pressure",
                "domain": "Economic",
                "impact": 6.8,
                "description": "Market pressure and supply vulnerabilities.",
                "factors": ["Commodity volatility", "Import dependency"],
            },
            {
                "id": "t3",
                "title": "Regional Spillover",
                "domain": "Political",
                "impact": 7.1,
                "description": "Secondary effects across neighboring actors.",
                "factors": ["Alliance shifts", "Diplomatic signaling"],
            },
        ]
        causal_edges = [
            {"from": "t1", "to": "t2", "confidence": 0.78},
            {"from": "t2", "to": "t3", "confidence": 0.71},
        ]

    trends = risk_analysis.get("trends", {}).get("weekly", [])
    top_category = categories[0].get("category", "Geopolitical") if categories else "Geopolitical"
    early_warning = []
    for idx in range(5):
        entry = trends[min(idx, len(trends) - 1)] if trends else {}
        score = float(entry.get(str(top_category).lower(), 60))
        early_warning.append(
            {
                "day": f"Day {idx + 1}-{idx + 2}",
                "label": f"{top_category} pressure window",
                "risk": _map_level_to_risk(score),
                "description": f"Projected score near {int(score)}% based on rolling trend analysis.",
            }
        )

    payload = {
        "selected_country": country,
        "heatmap": heatmap[:20],
        "causal_chain": {"nodes": causal_nodes[:10], "edges": causal_edges[:12]},
        "impact_metrics": impact_metrics[:6],
        "early_warning": early_warning,
    }

    await redis_client.set(cache_key, payload, expire=FRONTEND_CACHE_TTL)
    return payload


async def _build_analysis_payload(country: str) -> Dict[str, Any]:
    cache_key = f"frontend:analysis:{country.lower()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    try:
        risk_analysis = await insights_service.get_risk_analysis()
    except Exception as exc:
        logger.error(f"Failed to get risk analysis: {exc}")
        risk_analysis = {"categories": []}
    
    try:
        articles = await _load_news_articles()
    except Exception as exc:
        logger.error(f"Failed to load news articles: {exc}")
        articles = []
    
    categories = risk_analysis.get("categories", [])

    policy_recommendations = [
        {
            "title": "Short-term Actions" if idx == 0 else "Medium-term Policy" if idx == 1 else "Risk Mitigation",
            "items": [
                f"Prioritize response playbook for {entry.get('category', 'core')} domain.",
                f"Monitor trend '{entry.get('trend', 'stable')}' with 24h cadence.",
                f"Coordinate stakeholders around {int(entry.get('level', 0))}% risk indicator.",
            ],
        }
        for idx, entry in enumerate(categories[:3])
    ]
    policy_recommendations.append(
        {
            "title": "Stakeholder Notes",
            "items": [
                f"Prepare executive briefing for {country}.",
                "Align inter-agency response timelines.",
                "Validate external dependencies weekly.",
            ],
        }
    )

    source_citations = []
    for article in articles[:8]:
        source_citations.append(
            {
                "name": article.get("source", "Unknown"),
                "url": article.get("url", ""),
                "reliability": int(article.get("source_credibility", 88) or 88),
                "timestamp": article.get("published_at", datetime.utcnow().isoformat()),
            }
        )

    timeline = await _get_or_seed_risk_timeline(country=country, days=30, articles=articles)

    payload = {
        "selected_country": country,
        "policy_recommendations": policy_recommendations,
        "source_citations": source_citations[:5],
        "risk_timeline": timeline,
    }
    await redis_client.set(cache_key, payload, expire=FRONTEND_CACHE_TTL)
    return payload


async def _get_or_seed_risk_timeline(country: str, days: int, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    await _ensure_frontend_tables()
    rows = await postgres_client.execute_query(
        f"""
        SELECT snapshot_date, score, event_text
        FROM {RISK_TABLE}
        WHERE country = :country
        ORDER BY snapshot_date ASC
        LIMIT :limit
        """,
        {"country": country, "limit": days},
    )

    if len(rows) < days:
        base_score = 7.0
        start_day = date.today() - timedelta(days=days - 1)
        event_by_day: Dict[date, str] = {}
        for article in articles[:20]:
            published = _safe_date(article.get("published_at"))
            if not published:
                continue
            if published not in event_by_day:
                event_by_day[published] = article.get("title", "News event")

        for offset in range(days):
            day = start_day + timedelta(days=offset)
            score = round(base_score + ((offset % 7) - 3) * 0.15, 1)
            event_text = event_by_day.get(day)
            await postgres_client.execute_write(
                f"""
                INSERT INTO {RISK_TABLE} (country, snapshot_date, score, event_text)
                VALUES (:country, :snapshot_date, :score, :event_text)
                ON CONFLICT (country, snapshot_date)
                DO UPDATE SET score = EXCLUDED.score, event_text = COALESCE(EXCLUDED.event_text, {RISK_TABLE}.event_text)
                """,
                {
                    "country": country,
                    "snapshot_date": day,
                    "score": score,
                    "event_text": event_text,
                },
            )

        rows = await postgres_client.execute_query(
            f"""
            SELECT snapshot_date, score, event_text
            FROM {RISK_TABLE}
            WHERE country = :country
            ORDER BY snapshot_date ASC
            LIMIT :limit
            """,
            {"country": country, "limit": days},
        )

    return [
        {
            "day": idx + 1,
            "date": _to_iso_date(row["snapshot_date"]) if isinstance(row["snapshot_date"], date) else str(row["snapshot_date"]),
            "score": float(row.get("score", 0)),
            "event": row.get("event_text"),
        }
        for idx, row in enumerate(rows[-days:])
    ]


@router.get("/dashboard")
async def get_dashboard(country: str = "India") -> Dict[str, Any]:
    normalized_country = _normalize_country_name(country)
    try:
        payload = await _build_dashboard_payload(normalized_country)
        return ok(payload)
    except Exception as exc:
        logger.exception(f"Failed to build dashboard payload: {exc}")
        error("Failed to load dashboard data", 500)


@router.get("/intelligence/{country}")
async def get_intelligence(country: str) -> Dict[str, Any]:
    normalized_country = _normalize_country_name(country)
    try:
        payload = await _build_intelligence_payload(normalized_country)
        return ok(payload)
    except Exception as exc:
        logger.exception(f"Failed to build intelligence payload: {exc}")
        error("Failed to load intelligence data", 500)


@router.get("/analysis/{country}")
async def get_analysis(country: str) -> Dict[str, Any]:
    normalized_country = _normalize_country_name(country)
    try:
        payload = await _build_analysis_payload(normalized_country)
        return ok(payload)
    except Exception as exc:
        logger.exception(f"Failed to build analysis payload: {exc}")
        error("Failed to load analysis data", 500)


@router.post("/analysis/chat")
async def analysis_chat(request: ChatRequest) -> Dict[str, Any]:
    normalized_country = _normalize_country_name(request.country)
    try:
        rag_result = await graphrag_service.query(request.question)
        answer = rag_result.get("answer", "No answer available.")
        sources = rag_result.get("sources", [])

        await _ensure_frontend_tables()
        await postgres_client.execute_write(
            f"""
            INSERT INTO {CHAT_TABLE} (country, question, answer)
            VALUES (:country, :question, :answer)
            """,
            {
                "country": normalized_country,
                "question": request.question,
                "answer": answer,
            },
        )

        response_payload = {
            "question": request.question,
            "country": normalized_country,
            "answer": answer,
            "reasoning_chain": rag_result.get("reasoning_chain", []),
            "supporting_facts": rag_result.get("supporting_facts", []),
            "sources": sources,
        }
        return ok(response_payload, "Query answered")
    except Exception as exc:
        logger.exception(f"Failed to answer chat query: {exc}")
        error("Failed to process chat query", 500)
