"""
Ingestion Module - News and Data Collection
"""
from app.ingestion.news_ingestor import news_ingestor, NewsIngestor
from app.ingestion.deduplicator import NewsDeduplicator
from app.ingestion.entity_extractor import NewsEntityExtractor
from app.ingestion.graph_updater import GraphUpdater, graph_updater
from app.ingestion.pipeline import IngestionPipeline, ingestion_pipeline

__all__ = [
    "news_ingestor",
    "NewsIngestor",
    "NewsDeduplicator",
    "NewsEntityExtractor",
    "GraphUpdater",
    "graph_updater",
    "IngestionPipeline",
    "ingestion_pipeline",
]
