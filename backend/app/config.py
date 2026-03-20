"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Global Ontology Engine"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Neo4j Graph Database
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "ontology123"
    NEO4J_DATABASE: str = "neo4j"
    
    # PostgreSQL Database
    DATABASE_URL: str = "postgresql://ontology_user:ontology123@localhost:5432/ontology_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL_GPT4: str = "gpt-4-turbo-preview"
    OPENAI_MODEL_GPT35: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # News APIs
    NEWS_API_KEY: Optional[str] = None
    
    # RSS Feed Sources
    RSS_FEEDS: list = [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.npr.org/1004/rss.xml",
        "https://www.theguardian.com/world/rss",
        "https://www.dw.com/en/top-stories/rss",
        "https://www.france24.com/en/rss"
    ]
    
    # Data Ingestion Settings
    INGESTION_INTERVAL_MINUTES: int = 30
    MAX_ARTICLES_PER_INGESTION: int = 100
    
    # GraphRAG Settings
    MAX_CONTEXT_ENTITIES: int = 50
    MAX_CONTEXT_RELATIONS: int = 100
    MAX_HOPS: int = 3
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
