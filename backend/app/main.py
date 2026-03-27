"""
Global Ontology Engine - Main FastAPI Application
"""
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api import api_router
from app.database.neo4j_client import neo4j_client
from app.database.postgres_client import postgres_client
from app.database.redis_client import redis_client
from app.realtime.event_consumer import redis_event_consumer
from app.realtime.ingestion_pipeline import realtime_ingestion_pipeline
from app.realtime.websocket_server import ws_router
from app.ontology import ontology_service


async def create_fulltext_indexes() -> None:
    query = """
    CREATE FULLTEXT INDEX entity_name_ft IF NOT EXISTS
    FOR (n:Entity)
    ON EACH [n.name];
    """
    await neo4j_client.execute_query(query)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database connections - LOG WARNING on failures but continue
    try:
        await neo4j_client.connect()
        logger.info("Neo4j connection established")
        try:
            await ontology_service.ensure_search_indexes()
            await create_fulltext_indexes()
            logger.info("Ontology search indexes ensured")
        except Exception as e:
            logger.warning(f"Failed to ensure ontology search indexes: {e}")
    except Exception as e:
        logger.warning(f"Failed to connect to Neo4j: {e}")

    try:
        await postgres_client.connect()
        from app.api.endpoints.frontend import _ensure_frontend_tables
        from app.api.endpoints.news import _ensure_articles_table

        await _ensure_frontend_tables()
        await _ensure_articles_table()
        logger.info("PostgreSQL connection established")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise

    try:
        await redis_client.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
    
    app.state.realtime_stop_event = asyncio.Event()
    app.state.realtime_consumer_task = asyncio.create_task(
        redis_event_consumer.run(app.state.realtime_stop_event)
    )

    if settings.startup_ingestion_enabled:
        try:
            logger.info(
                f"Startup ingestion enabled (limit={settings.startup_ingestion_limit}); running ingestion"
            )
            ingestion_result = await realtime_ingestion_pipeline.run_once(
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

    if hasattr(app.state, "realtime_stop_event"):
        app.state.realtime_stop_event.set()
    if hasattr(app.state, "realtime_consumer_task"):
        try:
            await app.state.realtime_consumer_task
        except Exception:
            pass
    
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


@app.on_event("startup")
async def create_indexes():
    try:
        if not neo4j_client.driver:
            await neo4j_client.connect()
        await create_fulltext_indexes()
    except Exception as e:
        logger.warning(f"Failed to create startup full-text index: {e}")

# Import limiter after app creation to avoid circular import
from app.limiter import limiter

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization", 
        "X-Requested-With",
        "Accept",
        "Cache-Control",
        "X-Client-Version",
        "X-Request-ID"
    ],
    expose_headers=["X-Request-ID"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(ws_router)


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


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Avoid noisy 404 logs when browsers request favicon."""
    return Response(status_code=204)


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
