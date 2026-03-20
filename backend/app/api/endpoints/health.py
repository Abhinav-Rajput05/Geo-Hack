"""
Health Check API Endpoints
"""
from fastapi import APIRouter

from app.database import neo4j_client, postgres_client, redis_client

router = APIRouter()


@router.get("")
async def health():
    """
    Comprehensive health check for all services
    """
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


@router.get("/neo4j")
async def neo4j_health():
    """Check Neo4j health specifically"""
    status = await neo4j_client.health_check()
    return {"service": "neo4j", "status": "healthy" if status else "unhealthy"}


@router.get("/postgres")
async def postgres_health():
    """Check PostgreSQL health specifically"""
    status = await postgres_client.health_check()
    return {"service": "postgres", "status": "healthy" if status else "unhealthy"}


@router.get("/redis")
async def redis_health():
    """Check Redis health specifically"""
    status = await redis_client.health_check()
    return {"service": "redis", "status": "healthy" if status else "unhealthy"}
