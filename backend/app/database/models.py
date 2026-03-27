"""
PostgreSQL Database Models
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ARRAY, JSON, Index
from sqlalchemy.sql import func
from app.database.postgres_client import Base


class Article(Base):
    """News article model for persistent storage"""
    __tablename__ = "articles"
    
    id = Column(String(255), primary_key=True, index=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    content = Column(Text)
    source = Column(String(255), nullable=False, index=True)
    url = Column(Text, unique=True, index=True)
    published_at = Column(DateTime, nullable=False, index=True)
    
    # JSON fields for structured data
    categories = Column(ARRAY(String), default=[])
    entities = Column(JSON, default=[])
    location = Column(JSON)
    
    # Metadata
    domain = Column(String(100), index=True)
    region = Column(String(100), index=True)
    sentiment = Column(String(50))
    relevance_score = Column(Float)
    source_credibility = Column(Float)
    event_key = Column(String(255), index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_published_source', 'published_at', 'source'),
        Index('idx_region_domain', 'region', 'domain'),
    )


class User(Base):
    """User model for authentication/session tracking"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)
