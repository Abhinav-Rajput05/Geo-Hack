"""
Global Ontology Engine - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.config import settings
from app.api import api_router
from app.database.neo4j_client import neo4j_client
from app.database.postgres_client import postgres_client
from app.database.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database connections
    try:
        await neo4j_client.connect()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
    
    try:
        await postgres_client.connect()
        logger.info("PostgreSQL connection established")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
    
    try:
        await redis_client.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
    
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
