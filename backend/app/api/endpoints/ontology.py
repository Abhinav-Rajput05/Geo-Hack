"""
Ontology API Endpoints - Knowledge Graph Management
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.ontology import ontology_service

router = APIRouter()


class EntityType(BaseModel):
    """Entity type definition"""
    name: str
    description: str
    properties: List[str]
    count: int


class RelationshipType(BaseModel):
    """Relationship type definition"""
    name: str
    description: str
    source_types: List[str]
    target_types: List[str]
    properties: List[str]
    count: int


class Entity(BaseModel):
    """Entity model"""
    id: str
    name: str
    type: str
    properties: Dict[str, Any]
    relationships_count: int
    last_updated: str


class GraphStats(BaseModel):
    """Graph statistics"""
    total_nodes: int
    total_relationships: int
    entity_types: Dict[str, int]
    relationship_types: Dict[str, int]
    last_updated: str


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats():
    """
    Get knowledge graph statistics
    """
    try:
        stats = await ontology_service.get_graph_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph statistics: {e}") from e

    return GraphStats(
        total_nodes=stats.get("total_nodes", 0),
        total_relationships=stats.get("total_relationships", 0),
        entity_types=stats.get("entity_types", {}),
        relationship_types=stats.get("relationship_types", {}),
        last_updated=stats.get("last_updated", ""),
    )


@router.get("/entity-types", response_model=List[EntityType])
async def get_entity_types():
    """
    Get all entity types in the ontology
    """
    try:
        # Get actual counts from the database instead of hardcoded values
        stats = await ontology_service.get_graph_statistics()
        entity_types_data = stats.get("entity_types", {})
        
        # Define type metadata
        type_metadata = {
            "Country": {
                "description": "Nation states and territories",
                "properties": ["name", "code", "region", "population", "gdp"]
            },
            "Organization": {
                "description": "International organizations, alliances, NGOs",
                "properties": ["name", "type", "founded", "headquarters"]
            },
            "Company": {
                "description": "Corporations and business entities",
                "properties": ["name", "industry", "revenue", "headquarters"]
            },
            "Individual": {
                "description": "Notable persons (leaders, officials, experts)",
                "properties": ["name", "role", "country", "organization"]
            },
            "System": {
                "description": "Technological, military, or infrastructure systems",
                "properties": ["name", "type", "operator", "status"]
            },
            "Event": {
                "description": "Occurrences with temporal and spatial context",
                "properties": ["title", "date", "location", "type", "severity"]
            }
        }
        
        # Build response with real counts
        entity_types = []
        for type_name, count in entity_types_data.items():
            metadata = type_metadata.get(type_name, {
                "description": f"Entity type: {type_name}",
                "properties": ["name", "type"]
            })
            entity_types.append(EntityType(
                name=type_name,
                description=metadata["description"],
                properties=metadata["properties"],
                count=count
            ))
        
        # Sort by count descending
        entity_types.sort(key=lambda x: x.count, reverse=True)
        return entity_types
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch entity types: {e}") from e


@router.get("/relationship-types", response_model=List[RelationshipType])
async def get_relationship_types():
    """
    Get all relationship types in the ontology
    """
    return [
        RelationshipType(
            name="alliesWith",
            description="Formal alliance or partnership",
            source_types=["Country", "Organization"],
            target_types=["Country", "Organization"],
            properties=["since", "type"],
            count=450
        ),
        RelationshipType(
            name="tradesWith",
            description="Trade relationship between entities",
            source_types=["Country", "Company"],
            target_types=["Country", "Company"],
            properties=["volume", "goods", "since"],
            count=2800
        ),
        RelationshipType(
            name="sanctions",
            description="Sanctions imposed by one entity on another",
            source_types=["Country", "Organization"],
            target_types=["Country", "Company", "Individual"],
            properties=["type", "since", "reason"],
            count=120
        ),
        RelationshipType(
            name="supplies",
            description="Supply chain relationship",
            source_types=["Country", "Company"],
            target_types=["Country", "Company", "System"],
            properties=["product", "volume", "critical"],
            count=1500
        ),
        RelationshipType(
            name="dependsOn",
            description="Critical dependency relationship",
            source_types=["Country", "Company", "System"],
            target_types=["Country", "Company", "System"],
            properties=["type", "level", "critical"],
            count=3200
        ),
        RelationshipType(
            name="competesWith",
            description="Competitive relationship",
            source_types=["Country", "Company"],
            target_types=["Country", "Company"],
            properties=["domain", "intensity"],
            count=890
        ),
        RelationshipType(
            name="influences",
            description="Political or economic influence",
            source_types=["Country", "Organization", "Individual"],
            target_types=["Country", "Organization", "Company"],
            properties=["type", "strength"],
            count=2100
        )
    ]


@router.get("/entities/{entity_id}", response_model=Entity)
async def get_entity(entity_id: str):
    """
    Get a specific entity by ID
    """
    try:
        entity = await ontology_service.get_entity(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
        
        return Entity(
            id=entity_id,
            name=entity.get("name", "Unknown"),
            type=entity.get("type", "Unknown"),
            properties=entity.get("properties", {}),
            relationships_count=entity.get("relationships_count", 0),
            last_updated=entity.get("updated_at", datetime.utcnow().isoformat()),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch entity: {e}") from e


@router.get("/entities/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: str,
    relationship_type: Optional[str] = None,
    direction: str = "both",
    limit: int = 50
):
    """Get relationships for a specific entity"""
    try:
        relationships = await ontology_service.get_relationships(
            entity_id,
            relationship_type=relationship_type,
            direction=direction,
            limit=limit
        )
        return {
            "entity_id": entity_id,
            "relationships": relationships,
            "total": len(relationships)
        }
    except Exception as e:
        logger.warning(f"Relationships fetch failed for {entity_id}: {e}")
        # Return empty instead of 500 — graceful degradation
        return {
            "entity_id": entity_id,
            "relationships": [],
            "total": 0
        }


@router.get("/search")
async def search_entities(
    query: str,
    entity_type: Optional[str] = None,
    limit: int = 20
):
    """
    Search entities in the knowledge graph
    """
    if not query:
        return {
            "query": query,
            "results": [],
            "total": 0,
        }

    try:
        results = await ontology_service.search_entities(
            query=query,
            entity_type=entity_type,
            limit=limit
        )
        return {
            "query": query,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search entities: {e}") from e


@router.get("/graph/{entity_id}/subgraph")
async def get_entity_subgraph(
    entity_id: str,
    depth: int = 2,
    limit: int = 100
):
    """
    Get a subgraph centered on an entity for visualization
    """
    try:
        # Clamp depth to prevent performance issues
        clamped_depth = max(1, min(depth, 5))
        subgraph = await ontology_service.get_entity_subgraph(
            entity_id,
            depth=clamped_depth,
            limit=limit
        )
        return {
            "center": subgraph.get("center", {"id": entity_id}),
            "nodes": subgraph.get("nodes", []),
            "edges": subgraph.get("edges", []),
            "depth": clamped_depth
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch subgraph: {e}") from e


@router.get("/graph")
async def get_full_graph(limit: int = 80):
    """
    Get full knowledge graph nodes and edges for visualization
    """
    try:
        from app.database.neo4j_client import neo4j_client

        nodes_result = await neo4j_client.execute_query(
            """
            MATCH (e:Entity)
            RETURN id(e) as id, e.name as name, e.type as type
            ORDER BY e.type, e.name
            LIMIT $limit
            """,
            {"limit": limit},
        )

        node_ids = {row["id"] for row in nodes_result}

        edges_result = await neo4j_client.execute_query(
            """
            MATCH (a:Entity)-[r]->(b:Entity)
            WHERE id(a) IN $ids AND id(b) IN $ids
            RETURN id(a) as source, id(b) as target,
                   coalesce(r.type, type(r)) as type
            LIMIT $limit
            """,
            {"ids": list(node_ids), "limit": limit * 3},
        )

        nodes = [
            {"id": str(row["id"]), "name": row["name"] or "Unknown", "type": row["type"] or "Entity"}
            for row in nodes_result
        ]
        edges = [
            {"source": str(row["source"]), "target": str(row["target"]), "type": row["type"] or "RELATES"}
            for row in edges_result
        ]

        return {"nodes": nodes, "edges": edges}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph: {e}") from e


@router.get("/entities")
async def list_entities(
    entity_type: Optional[str] = None,
    limit: int = 60,
):
    """List entities for graph explorer fallback"""
    try:
        from app.database.neo4j_client import neo4j_client

        if entity_type:
            result = await neo4j_client.execute_query(
                "MATCH (e:Entity {type: $t}) RETURN id(e) as id, e.name as name, e.type as type LIMIT $limit",
                {"t": entity_type, "limit": limit},
            )
        else:
            result = await neo4j_client.execute_query(
                "MATCH (e:Entity) RETURN id(e) as id, e.name as name, e.type as type ORDER BY e.type LIMIT $limit",
                {"limit": limit},
            )

        return [
            {"id": str(row["id"]), "name": row["name"] or "Unknown", "type": row["type"] or "Entity"}
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list entities: {e}") from e
