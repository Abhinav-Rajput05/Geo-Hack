"""
Neo4j Graph Database Client
"""
import re
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional, List, Dict, Any
from loguru import logger

from app.config import settings


# Validation regex for Neo4j labels and relationship types
# Must start with letter or underscore, followed by alphanumeric or underscores
LABEL_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def validate_label(label: str) -> bool:
    """Validate that a label is safe for use in Cypher queries"""
    return bool(LABEL_PATTERN.match(label))


def validate_relationship_type(rel_type: str) -> bool:
    """Validate that a relationship type is safe for use in Cypher queries"""
    return bool(LABEL_PATTERN.match(rel_type))


class Neo4jClient:
    """Async Neo4j client for graph database operations"""
    
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.database = settings.NEO4J_DATABASE
    
    async def connect(self) -> None:
        """Establish connection to Neo4j database"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            async with self.driver.session(database=self.database) as session:
                await session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self) -> None:
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")
    
    async def health_check(self) -> bool:
        """Check if Neo4j is healthy"""
        try:
            if not self.driver:
                return False
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
                return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results"""
        params: Dict[str, Any] = {}
        if parameters:
            params.update(parameters)
        if kwargs:
            params.update(kwargs)
        
        try:
            if not self.driver:
                raise RuntimeError("Neo4j driver is not connected")
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, params)
                records = [record.data() async for record in result]
                return records
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise
    
    async def execute_write(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Any:
        """Execute a write transaction using session.execute_write for proper leader routing"""
        params: Dict[str, Any] = {}
        if parameters:
            params.update(parameters)
        if kwargs:
            params.update(kwargs)
        
        try:
            if not self.driver:
                raise RuntimeError("Neo4j driver is not connected")
            
            async with self.driver.session(database=self.database) as session:
                # Use execute_write for proper leader routing and automatic retries
                # This ensures writes are routed to the leader in a Neo4j cluster
                async def write_transaction(tx):
                    result = await tx.run(query, params)
                    return await result.consume()
                
                summary = await session.execute_write(write_transaction)
                return summary
        except Exception as e:
            logger.error(f"Write execution failed: {e}\nQuery: {query}")
            raise
    
    async def create_node(
        self, 
        label: str, 
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a node with given label and properties"""
        # Validate label to prevent Cypher injection
        if not validate_label(label):
            raise ValueError(f"Invalid label format: {label}")
        
        query = f"""
        CREATE (n:`{label}` $props)
        RETURN n
        """
        result = await self.execute_query(query, {"props": properties})
        return result[0] if result else None
    
    async def create_relationship(
        self,
        from_node_id: int,
        to_node_id: int,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a relationship between two nodes"""
        if properties is None:
            properties = {}
        
        # Validate relationship type to prevent Cypher injection
        if not validate_relationship_type(relationship_type):
            raise ValueError(f"Invalid relationship type format: {relationship_type}")
        
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $from_id AND id(b) = $to_id
        CREATE (a)-[r:`{relationship_type}` $props]->(b)
        RETURN r
        """
        result = await self.execute_query(
            query, 
            {"from_id": from_node_id, "to_id": to_node_id, "props": properties}
        )
        return result[0] if result else None
    
    async def find_node(
        self, 
        label: str, 
        property_name: str, 
        property_value: Any
    ) -> Optional[Dict[str, Any]]:
        """Find a node by property value"""
        # Validate label to prevent Cypher injection
        if not validate_label(label):
            raise ValueError(f"Invalid label format: {label}")
        
        # Validate property name (column name) to prevent Cypher injection
        if not validate_label(property_name):
            raise ValueError(f"Invalid property name format: {property_name}")
        
        query = f"""
        MATCH (n:`{label}` {{{property_name}: $value}})
        RETURN n
        """
        result = await self.execute_query(query, {"value": property_value})
        return result[0] if result else None
    
    async def get_node_by_id(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Get a node by its internal ID"""
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        RETURN n
        """
        result = await self.execute_query(query, {"node_id": node_id})
        return result[0] if result else None
    
    async def get_related_nodes(
        self,
        node_id: int,
        relationship_types: Optional[List[str]] = None,
        max_hops: int = 1
    ) -> List[Dict[str, Any]]:
        """Get nodes related to a given node"""
        # Clamp max_hops to prevent cartesian explosion
        max_hops = max(1, min(max_hops, 5))
        
        if relationship_types:
            # Validate all relationship types to prevent Cypher injection
            for rel_type in relationship_types:
                if not validate_relationship_type(rel_type):
                    raise ValueError(f"Invalid relationship type format: {rel_type}")
            
            rel_pattern = "|".join(f"`{rel_type}`" for rel_type in relationship_types)
            rel_query = f"[r:{rel_pattern}*1..{max_hops}]"
        else:
            rel_query = f"[r*1..{max_hops}]"
        
        query = f"""
        MATCH (n)-{rel_query}-(related)
        WHERE id(n) = $node_id
        RETURN DISTINCT related, r
        """
        result = await self.execute_query(query, {"node_id": node_id})
        return result

    async def create_article_graph(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create or update article graph nodes and relationships."""
        categories = article.get("categories") or []
        if not isinstance(categories, list):
            categories = []

        query = """
        MERGE (a:Article {url: $url})
        ON CREATE SET a.created_at = datetime()
        SET a.title = $title,
            a.summary = $summary,
            a.content = $content,
            a.source = $source,
            a.author = $author,
            a.image_url = $image_url,
            a.published_at = $published_at,
            a.ingested_at = $ingested_at,
            a.status = $status,
            a.updated_at = datetime()
        MERGE (s:Source {name: $source})
        ON CREATE SET s.created_at = datetime()
        SET s.last_seen_at = datetime()
        MERGE (a)-[pub:PUBLISHED_BY]->(s)
        ON CREATE SET pub.created_at = datetime()
        SET pub.last_seen_at = datetime()
        WITH a
        FOREACH (cat IN $categories |
            MERGE (c:Category {name: cat})
            ON CREATE SET c.created_at = datetime()
            MERGE (a)-[:IN_CATEGORY]->(c)
        )
        RETURN id(a) AS article_id, a.url AS url, a.title AS title
        """

        result = await self.execute_query(
            query,
            {
                "url": article.get("url"),
                "title": article.get("title", "Untitled"),
                "summary": article.get("summary", ""),
                "content": article.get("content"),
                "source": article.get("source", "Unknown"),
                "author": article.get("author"),
                "image_url": article.get("image_url"),
                "published_at": article.get("published_at"),
                "ingested_at": article.get("ingested_at"),
                "status": article.get("status", "pending"),
                "categories": categories,
            },
        )
        return result[0] if result else None


# Global Neo4j client instance
neo4j_client = Neo4jClient()
