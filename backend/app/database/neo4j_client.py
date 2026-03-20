"""
Neo4j Graph Database Client
"""
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional, List, Dict, Any
from loguru import logger

from app.config import settings


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
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results"""
        if parameters is None:
            parameters = {}
        
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, parameters)
                records = [record.data() async for record in result]
                return records
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise
    
    async def execute_write(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a write transaction"""
        if parameters is None:
            parameters = {}
        
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, parameters)
                summary = await result.consume()
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
        query = f"""
        CREATE (n:{label} $props)
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
        
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $from_id AND id(b) = $to_id
        CREATE (a)-[r:{relationship_type} $props]->(b)
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
        query = f"""
        MATCH (n:{label} {{{property_name}: $value}})
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
        if relationship_types:
            rel_pattern = "|".join(relationship_types)
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


# Global Neo4j client instance
neo4j_client = Neo4jClient()
