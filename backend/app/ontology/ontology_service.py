"""
Ontology Service - Core Knowledge Graph Operations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.ontology.schema import Entity, EntityType, Relationship, RelationshipType
from app.database.neo4j_client import neo4j_client


class OntologyService:
    """Service for managing knowledge graph operations"""
    
    def __init__(self):
        self.neo4j = neo4j_client
    
    async def create_entity(self, entity: Entity) -> Dict[str, Any]:
        """Create a new entity in the knowledge graph"""
        query = """
        MERGE (e:Entity {name: $name, type: $type})
        SET e += $properties,
            e.description = $description,
            e.confidence = $confidence,
            e.sources = $sources,
            e.created_at = $created_at,
            e.updated_at = $updated_at
        RETURN e
        """
        result = await self.neo4j.execute_query(
            query,
            name=entity.name,
            type=entity.type,
            properties=entity.properties,
            description=entity.description,
            confidence=entity.confidence,
            sources=entity.sources,
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat()
        )
        return result[0] if result else None
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        query = """
        MATCH (e:Entity)
        WHERE e.name = $entity_id OR id(e) = $entity_id
        RETURN e, id(e) as node_id
        """
        result = await self.neo4j.execute_query(query, entity_id=str(entity_id))
        if result:
            node = result[0]['e']
            node['id'] = str(result[0]['node_id'])
            return node
        return None
    
    async def search_entities(
        self, 
        query: str, 
        entity_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search entities by name or type"""
        cypher = """
        MATCH (e:Entity)
        WHERE e.name CONTAINS $query
        """
        if entity_type:
            cypher += " AND e.type = $entity_type"
        
        cypher += """
        RETURN e, id(e) as node_id
        ORDER BY e.name
        LIMIT $limit
        """
        
        results = await self.neo4j.execute_query(
            cypher, 
            query=query, 
            entity_type=entity_type,
            limit=limit
        )
        
        entities = []
        for row in results:
            entity = dict(row['e'])
            entity['id'] = str(row['node_id'])
            entities.append(entity)
        
        return entities
    
    async def create_relationship(self, relationship: Relationship) -> Dict[str, Any]:
        """Create a new relationship between entities"""
        query = """
        MATCH (source:Entity), (target:Entity)
        WHERE id(source) = $source_id OR source.name = $source_id
        WHERE id(target) = $target_id OR target.name = $target_id
        MERGE (source)-[r:RELATES {type: $type}]->(target)
        SET r += $properties,
            r.confidence = $confidence,
            r.sources = $sources,
            r.created_at = $created_at
        RETURN source, r, target
        """
        result = await self.neo4j.execute_query(
            query,
            source_id=relationship.source_id,
            target_id=relationship.target_id,
            type=relationship.type,
            properties=relationship.properties,
            confidence=relationship.confidence,
            sources=relationship.sources,
            created_at=relationship.created_at.isoformat()
        )
        return result[0] if result else None
    
    async def get_relationships(
        self, 
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "both",  # outgoing, incoming, both
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get relationships for an entity"""
        
        if direction == "outgoing":
            dir_query = "(e)-[r]->(target)"
        elif direction == "incoming":
            dir_query = "(source)-[r]->(e)"
        else:
            dir_query = "(e)-[r]->(target), (source)-[r2]->(e)"
        
        query = f"""
        MATCH {dir_query}
        WHERE id(e) = $entity_id OR e.name = $entity_id
        """
        
        if relationship_type:
            query += " AND r.type = $relationship_type"
        
        query += """
        RETURN source, r, target, id(r) as rel_id
        LIMIT $limit
        """
        
        results = await self.neo4j.execute_query(
            query,
            entity_id=str(entity_id),
            relationship_type=relationship_type,
            limit=limit
        )
        
        relationships = []
        for row in results:
            rel = {
                'id': str(row['rel_id']),
                'type': row['r'].get('type'),
                'properties': dict(row['r']),
                'source': dict(row['source']) if 'source' in row else None,
                'target': dict(row['target']) if 'target' in row else None,
            }
            relationships.append(rel)
        
        return relationships
    
    async def get_entity_subgraph(
        self, 
        entity_id: str, 
        depth: int = 2,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get a subgraph centered on an entity for visualization"""
        
        # Get connected nodes at specified depth
        query = f"""
        MATCH path = (e:Entity)-[r*1..{depth}]->(connected)
        WHERE id(e) = $entity_id OR e.name = $entity_id
        WITH nodes(path) as nodes, relationships(path) as rels
        UNWIND nodes as n
        UNWIND rels as r
        WITH DISTINCT n, r
        RETURN collect(DISTINCT {{
            id: id(n),
            name: n.name,
            type: n.type,
            properties: properties(n)
        }}) as nodes,
        collect(DISTINCT {{
            source: id(startNode(r)),
            target: id(endNode(r)),
            type: type(r),
            properties: properties(r)
        }}) as edges
        LIMIT 1
        """
        
        result = await self.neo4j.execute_query(
            query,
            entity_id=str(entity_id),
            depth=depth,
            limit=limit
        )
        
        if result:
            return result[0]
        return {'nodes': [], 'edges': []}
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        
        # Count total nodes and relationships
        stats_query = """
        MATCH (e:Entity)
        RETURN count(e) as total_nodes
        """
        node_result = await self.neo4j.execute_query(stats_query)
        
        rel_query = """
        MATCH ()-[r]->()
        RETURN count(r) as total_relationships
        """
        rel_result = await self.neo4j.execute_query(rel_query)
        
        # Count by entity type
        type_query = """
        MATCH (e:Entity)
        RETURN e.type as type, count(e) as count
        ORDER BY count DESC
        """
        type_results = await self.neo4j.execute_query(type_query)
        
        # Count by relationship type
        rel_type_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        rel_type_results = await self.neo4j.execute_query(rel_type_query)
        
        return {
            'total_nodes': node_result[0]['total_nodes'] if node_result else 0,
            'total_relationships': rel_result[0]['total_relationships'] if rel_result else 0,
            'entity_types': {row['type']: row['count'] for row in type_results},
            'relationship_types': {row['type']: row['count'] for row in rel_type_results},
            'last_updated': datetime.utcnow().isoformat()
        }
    
    async def get_related_entities(
        self, 
        entity_id: str, 
        types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get entities related to a given entity"""
        
        query = """
        MATCH (e:Entity)-[r]->(related:Entity)
        WHERE id(e) = $entity_id OR e.name = $entity_id
        """
        
        if types:
            query += " AND related.type IN $types"
        
        query += """
        RETURN related, type(r) as relationship_type, id(r) as rel_id
        ORDER BY r.confidence DESC
        LIMIT $limit
        """
        
        results = await self.neo4j.execute_query(
            query,
            entity_id=str(entity_id),
            types=types,
            limit=limit
        )
        
        entities = []
        for row in results:
            entity = dict(row['related'])
            entity['relationship_type'] = row['relationship_type']
            entity['rel_id'] = str(row['rel_id'])
            entities.append(entity)
        
        return entities
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and its relationships"""
        
        query = """
        MATCH (e:Entity)
        WHERE id(e) = $entity_id OR e.name = $entity_id
        DETACH DELETE e
        RETURN count(e) as deleted
        """
        
        result = await self.neo4j.execute_query(query, entity_id=str(entity_id))
        return result[0]['deleted'] > 0 if result else False
    
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship"""
        
        query = """
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        DELETE r
        RETURN count(r) as deleted
        """
        
        result = await self.neo4j.execute_query(query, rel_id=int(relationship_id))
        return result[0]['deleted'] > 0 if result else False


# Singleton instance
ontology_service = OntologyService()
