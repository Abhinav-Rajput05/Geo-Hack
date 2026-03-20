"""
API Router Module
"""
from fastapi import APIRouter

from app.api.endpoints import query, insights, news, ontology, health

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(query.router, prefix="/query", tags=["Query"])
api_router.include_router(insights.router, prefix="/insights", tags=["Insights"])
api_router.include_router(news.router, prefix="/news", tags=["News"])
api_router.include_router(ontology.router, prefix="/ontology", tags=["Ontology"])
