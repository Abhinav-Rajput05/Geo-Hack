"""
PostgreSQL Database Client
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from loguru import logger

from app.config import settings


# Convert postgresql:// to postgresql+asyncpg://
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


class PostgresClient:
    """Async PostgreSQL client using SQLAlchemy"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.database_url = DATABASE_URL
    
    async def connect(self) -> None:
        """Establish connection to PostgreSQL database"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=settings.DEBUG,
                pool_size=10,
                max_overflow=20
            )
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info(f"Connected to PostgreSQL at {self.database_url.split('@')[1] if '@' in self.database_url else self.database_url}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def close(self) -> None:
        """Close PostgreSQL connection"""
        if self.engine:
            await self.engine.dispose()
            logger.info("PostgreSQL connection closed")
    
    async def health_check(self) -> bool:
        """Check if PostgreSQL is healthy"""
        try:
            if not self.engine:
                return False
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        if not self.session_factory:
            raise RuntimeError("Database not connected")
        return self.session_factory()
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a raw SQL query and return results"""
        if not self.engine:
            raise RuntimeError("PostgreSQL not connected")
        if parameters is None:
            parameters = {}
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(query), parameters)
                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise
    
    async def execute_write(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Execute a write query and return affected rows"""
        if not self.engine:
            raise RuntimeError("PostgreSQL not connected")
        if parameters is None:
            parameters = {}
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(query), parameters)
                return result.rowcount
        except Exception as e:
            logger.error(f"Write execution failed: {e}\nQuery: {query}")
            raise

    async def execute_write_many(
        self,
        query: str,
        parameters: List[Dict[str, Any]],
    ) -> int:
        """Execute a parameterized write query for multiple rows in one transaction."""
        if not self.engine:
            raise RuntimeError("PostgreSQL not connected")
        if not parameters:
            return 0

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(query), parameters)
                return result.rowcount
        except Exception as e:
            logger.error(f"Batch write execution failed: {e}\nQuery: {query}")
            raise


# Base class for SQLAlchemy models
Base = declarative_base()

# Global PostgreSQL client instance
postgres_client = PostgresClient()
