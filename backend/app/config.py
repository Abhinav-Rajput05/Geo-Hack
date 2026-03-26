"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Global Ontology Engine"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False  # Changed from True for production safety
    
    # Neo4j Graph Database
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "neo4j"
    
    # PostgreSQL Database
    DATABASE_URL: str = "postgresql://ontology_user:ontology123@localhost:5432/ontology_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_NEWS_CHANNEL: str = "news:articles:live"
    
    # OpenRouter (OpenAI-compatible API)
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENAI_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_MODEL_GPT4: str = "gpt-4-turbo-preview"
    OPENAI_MODEL_GPT35: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # News APIs
    NEWS_API_KEY: Optional[str] = None
    GNEWS_API_KEY: Optional[str] = None
    GNEWS_BASE_URL: str = "https://gnews.io/api/v4/top-headlines"
    EVENT_REGISTRY_API_KEY: Optional[str] = None
    GDELT_ENABLED: bool = True
    
    # RSS Feed Sources
    RSS_FEEDS: list = [
        "https://feeds.reuters.com/reuters/topNews",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/worldNews",
    ]
    
    # Data Ingestion Settings
    INGESTION_INTERVAL_MINUTES: int = 5
    MAX_ARTICLES_PER_INGESTION: int = 150
    STARTUP_INGESTION_ENABLED: bool = True
    STARTUP_INGESTION_LIMIT: int = 5
    NEWS_FETCH_TIMEOUT_SECONDS: int = 8
    NEWS_FETCH_RETRIES: int = 3
    NEWS_MAX_CONCURRENT_FETCHES: int = 8
    NEWS_RATE_LIMIT_PER_SECOND: float = 8.0
    NEWS_MAX_CONCURRENT_ENRICHMENT: int = 4
    NEWS_DEDUP_SIMILARITY_THRESHOLD: float = 0.86
    NEWS_DEDUP_TTL_SECONDS: int = 21600
    NEWS_MAX_RAW_TEXT_CHARS: int = 9000
    NEWS_MAX_LLM_TEXT_CHARS: int = 2800
    NEWS_BATCH_SIZE: int = 25
    NEWS_USE_LLM_ENRICHMENT: bool = False
    NEWS_FEEDS_CONFIG_PATH: str = "app/ingestion/rss_feeds.json"
    NEWS_SEEN_HASHES_FILE: str = "data/seen_article_hashes.txt"
    WS_AUTH_TOKEN: Optional[str] = None
    WS_EVENT_THROTTLE_MS: int = 0
    
    # GraphRAG Settings
    GRAPHRAG_TOP_K: int = 5
    GRAPHRAG_MAX_HOPS: int = 3
    MAX_CONTEXT_ENTITIES: int = 50
    MAX_CONTEXT_RELATIONS: int = 100
    MAX_HOPS: int = 3
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        """Allow loose DEBUG values from env files."""
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        value_str = str(value).strip().lower()
        if value_str in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if value_str in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        return True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, list):
            return value
        if value is None:
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        value_str = str(value).strip()
        if "," in value_str:
            return [origin.strip() for origin in value_str.split(",") if origin.strip()]
        return [value_str] if value_str else [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    @field_validator("INGESTION_INTERVAL_MINUTES", mode="before")
    @classmethod
    def validate_ingestion_interval(cls, value):
        """Validate and set reasonable ingestion interval bounds"""
        try:
            numeric = int(value)
        except Exception:
            return 5  # Default to 5 minutes if invalid
        # Clamp to reasonable bounds: min 1 minute, max 60 minutes
        return max(1, min(60, numeric))

    @property
    def openai_api_key(self) -> str:
        return self.OPENROUTER_API_KEY

    @property
    def openai_base_url(self) -> str:
        return self.OPENROUTER_BASE_URL

    @property
    def openai_model(self) -> str:
        return self.OPENAI_MODEL or self.OPENAI_MODEL_GPT4

    @property
    def openai_embedding_model(self) -> str:
        return self.OPENAI_EMBEDDING_MODEL

    @property
    def openai_max_tokens(self) -> int:
        return self.OPENAI_MAX_TOKENS

    @property
    def rss_feeds(self) -> List[str]:
        return self.RSS_FEEDS

    @property
    def news_api_key(self) -> Optional[str]:
        return self.NEWS_API_KEY

    @property
    def graphrag_top_k(self) -> int:
        return self.GRAPHRAG_TOP_K

    @property
    def graphrag_max_hops(self) -> int:
        return self.GRAPHRAG_MAX_HOPS

    @property
    def startup_ingestion_enabled(self) -> bool:
        return self.STARTUP_INGESTION_ENABLED

    @property
    def startup_ingestion_limit(self) -> int:
        return self.STARTUP_INGESTION_LIMIT
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
