"""
Query API Endpoints - GraphRAG Question Answering
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from time import perf_counter

from app.graphrag import graphrag_service
from app.insights import insights_service
from app.ontology import ontology_service
from app.limiter import limiter

router = APIRouter()


class QueryRequest(BaseModel):
    """Query request model"""
    question: str
    domain: Optional[str] = None  # geopolitics, economics, defense, technology, climate, society
    max_hops: Optional[int] = 3
    include_sources: Optional[bool] = True
    include_map_data: Optional[bool] = False  # Optional, expensive operation
    include_risk_analysis: Optional[bool] = False  # Optional, expensive operation


class EntityReference(BaseModel):
    """Entity reference in answer"""
    name: str
    type: str
    relevance_score: float


class AnswerExplanation(BaseModel):
    """Detailed explanation of the answer"""
    reasoning_chain: List[str]
    supporting_facts: List[Dict[str, Any]]
    confidence_level: str  # high, medium, low
    data_sources: List[str]


class QueryResponse(BaseModel):
    """Query response model"""
    question: str
    answer: str
    explanation: AnswerExplanation
    entities: List[EntityReference]
    relationships: List[Dict[str, Any]]
    impact_map: Optional[Dict[str, Any]] = None  # Country-wise impact data
    risk_analysis: Optional[Dict[str, Any]] = None
    sources: List[Dict[str, Any]]
    query_time_ms: float


@router.post("", response_model=QueryResponse)
@limiter.limit("10/minute")  # Rate limit expensive GraphRAG queries
async def query_ontology(request: Request, query_request: QueryRequest):
    """
    Query the knowledge graph using GraphRAG
    
    This endpoint processes natural language questions and returns:
    - Comprehensive answer with detailed explanation
    - Related entities and relationships
    - Country-wise impact data for map visualization (optional, expensive)
    - Risk analysis with severity levels (optional, expensive)
    - Source citations
    """
    started = perf_counter()
    try:
        rag_result = await graphrag_service.query(query_request.question)
        
        # Only fetch expensive operations when explicitly requested
        map_data = None
        risk_data = None
        
        if query_request.include_map_data:
            map_data = await insights_service.get_map_data()
            
        if query_request.include_risk_analysis:
            risk_data = await insights_service.get_risk_analysis(category=query_request.domain)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {e}") from e

    supporting_facts = rag_result.get("supporting_facts", [])
    if not isinstance(supporting_facts, list):
        supporting_facts = []

    # Convert graph entities to API response shape.
    entities: List[EntityReference] = []
    for entity in rag_result.get("related_entities", []):
        name = entity.get("name", "Unknown")
        entity_type = entity.get("type", "Unknown")
        confidence = float(entity.get("confidence", 0.7))
        entities.append(
            EntityReference(
                name=name,
                type=entity_type,
                relevance_score=max(0.0, min(confidence, 1.0)),
            )
        )

    confidence_score = float(rag_result.get("confidence", 0.0))
    if confidence_score >= 0.75:
        confidence_level = "high"
    elif confidence_score >= 0.45:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    elapsed_ms = (perf_counter() - started) * 1000

    return QueryResponse(
        question=query_request.question,
        answer=rag_result.get("answer", "No answer available"),
        explanation=AnswerExplanation(
            reasoning_chain=rag_result.get("reasoning_chain", []),
            supporting_facts=supporting_facts,
            confidence_level=confidence_level,
            data_sources=["knowledge_graph", "llm_generation"],
        ),
        entities=entities,
        relationships=rag_result.get("relationships", []),
        impact_map=map_data,
        risk_analysis=risk_data,
        sources=rag_result.get("sources", []),
        query_time_ms=round(elapsed_ms, 2),
    )


@router.post("/entities")
async def search_entities(query: str, limit: int = 10):
    """
    Search for entities in the knowledge graph
    """
    try:
        candidates = await graphrag_service._extract_key_entities(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity search failed: {e}") from e

    entities = [{"name": name, "type": "Unknown"} for name in candidates[:limit]]
    return {"query": query, "entities": entities, "total": len(entities)}


@router.get("/suggestions")
async def get_query_suggestions(prefix: str, limit: int = 5):
    """Get query suggestions based on prefix"""
    try:
        # Step 1: Fetch matching entities from ontology service
        entities = await ontology_service.search_entities(
            query=prefix,
            limit=limit
        )

        # Step 2: Generate suggestions using templates
        suggestions = []

        templates = {
            "Country": "What is the current risk level for {name}?",
            "Organization": "What is {name}'s role in global affairs?",
            "Individual": "Tell me about {name}'s influence.",
            "Event": "What are the implications of {name}?",
            "Location": "What risks are associated with {name}?"
        }

        for entity in entities:
            entity_type = entity.get("type", "Unknown")
            name = entity.get("name", "")

            if not name:
                continue

            template = templates.get(
                entity_type,
                "Tell me about {name}."
            )

            suggestions.append(template.format(name=name))

        return {
            "success": True,
            "suggestions": suggestions
        }

    except Exception as e:
        return {
            "success": False,
            "suggestions": [],
            "error": str(e)
        }
