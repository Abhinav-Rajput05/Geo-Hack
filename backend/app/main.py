"""
Global Ontology Engine - Main FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api import api_router
from app.database.neo4j_client import neo4j_client
from app.database.postgres_client import postgres_client
from app.database.redis_client import redis_client
from app.ingestion.news_ingestor import news_ingestor

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database connections - FAIL FAST on critical database failures
    try:
        await neo4j_client.connect()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise RuntimeError("Cannot start application: Neo4j connection failed") from e
    
    try:
        await postgres_client.connect()
        logger.info("PostgreSQL connection established")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise RuntimeError("Cannot start application: PostgreSQL connection failed") from e
    
    try:
        await redis_client.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise RuntimeError("Cannot start application: Redis connection failed") from e

    if settings.startup_ingestion_enabled:
        try:
            logger.info(
                f"Startup ingestion enabled (limit={settings.startup_ingestion_limit}); running ingestion"
            )
            ingestion_result = await news_ingestor.ingest_all(
                limit_per_source=settings.startup_ingestion_limit
            )
            logger.info(
                "Startup ingestion finished: "
                f"unique_articles={ingestion_result.get('unique_articles', 0)}, "
                f"persisted_to_neo4j={ingestion_result.get('persisted_to_neo4j', 0)}"
            )
        except Exception as e:
            logger.error(f"Startup ingestion failed: {e}")
            # Don't fail startup for ingestion errors - this is non-critical
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    await neo4j_client.close()
    logger.info("Neo4j connection closed")
    
    await postgres_client.close()
    logger.info("PostgreSQL connection closed")
    
    await redis_client.close()
    logger.info("Redis connection closed")
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Global Ontology Engine for multi-domain knowledge graph and strategic insights",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "api": settings.API_PREFIX
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    neo4j_status = await neo4j_client.health_check()
    postgres_status = await postgres_client.health_check()
    redis_status = await redis_client.health_check()
    
    all_healthy = all([neo4j_status, postgres_status, redis_status])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "neo4j": "healthy" if neo4j_status else "unhealthy",
            "postgres": "healthy" if postgres_status else "unhealthy",
            "redis": "healthy" if redis_status else "unhealthy"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
