"""
Knowledge Graph Schema - Entity and Relationship Definitions
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class EntityType(str, Enum):
    """Entity types in the ontology"""
    COUNTRY = "Country"
    ORGANIZATION = "Organization"
    COMPANY = "Company"
    INDIVIDUAL = "Individual"
    SYSTEM = "System"
    EVENT = "Event"
    LOCATION = "Location"
    RESOURCE = "Resource"


class RelationshipType(str, Enum):
    """Relationship types in the ontology"""
    ALLIES_WITH = "alliesWith"
    TRADES_WITH = "tradesWith"
    SANCTIONS = "sanctions"
    SUPPLIES = "supplies"
    DEPENDS_ON = "dependsOn"
    COMPETES_WITH = "competesWith"
    INFLUENCES = "influences"
    LOCATED_IN = "locatedIn"
    PART_OF = "partOf"
    OCCURRED_IN = "occurredIn"
    MEMBER_OF = "memberOf"
    LEADS = "leads"
    OWNS = "owns"
    INVESTED_IN = "investedIn"
    PARTNERED_WITH = "partneredWith"
    THREATENS = "threatens"


class Entity(BaseModel):
    """Entity model for knowledge graph"""
    id: Optional[str] = None
    name: str = Field(..., description="Entity name")
    type: EntityType = Field(..., description="Entity type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    description: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class Relationship(BaseModel):
    """Relationship model for knowledge graph"""
    id: Optional[str] = None
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    type: RelationshipType = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# Entity property schemas per type
ENTITY_PROPERTIES = {
    EntityType.COUNTRY: {
        "code": "str",  # ISO country code
        "region": "str",
        "population": "int",
        "gdp": "float",
        "currency": "str",
        "government_type": "str",
        "alliances": "list",
    },
    EntityType.ORGANIZATION: {
        "name": "str",
        "type": "str",  # NGO, IGO, alliance, etc.
        "founded": "date",
        "headquarters": "str",
        "members": "list",
        "budget": "float",
    },
    EntityType.COMPANY: {
        "ticker": "str",
        "industry": "str",
        "revenue": "float",
        "market_cap": "float",
        "headquarters": "str",
        "ceo": "str",
        "founded": "date",
    },
    EntityType.INDIVIDUAL: {
        "role": "str",
        "title": "str",
        "birth_date": "date",
        "nationality": "str",
        "organization": "str",
        "net_worth": "float",
    },
    EntityType.SYSTEM: {
        "type": "str",  # Military, tech, infrastructure
        "operator": "str",
        "status": "str",  # Active, inactive, under development
        "capabilities": "list",
        "deployment": "list",
    },
    EntityType.EVENT: {
        "date": "date",
        "end_date": "date",
        "location": "str",
        "type": "str",  # Conflict, summit, election, disaster
        "severity": "int",  # 1-10
        "participants": "list",
        "outcome": "str",
    },
}

# Relationship property schemas
RELATIONSHIP_PROPERTIES = {
    RelationshipType.ALLIES_WITH: {
        "since": "date",
        "type": "str",  # Military, economic, diplomatic
        "treaty": "str",
    },
    RelationshipType.TRADES_WITH: {
        "volume": "float",  # In billions USD
        "goods": "list",
        "since": "date",
    },
    RelationshipType.SANCTIONS: {
        "type": "str",  # Economic, military, diplomatic
        "since": "date",
        "reason": "str",
        "severity": "int",
    },
    RelationshipType.SUPPLIES: {
        "product": "str",
        "volume": "float",
        "critical": "bool",
    },
    RelationshipType.DEPENDS_ON: {
        "type": "str",  # Energy, technology, resources
        "level": "str",  # Critical, high, medium, low
        "percentage": "float",
    },
    RelationshipType.INFLUENCES: {
        "type": "str",  # Political, economic, military
        "strength": "float",  # 0-1
        "mechanism": "str",
    },
}


# Risk level enum
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment(BaseModel):
    """Risk assessment for entities"""
    entity_id: str
    entity_name: str
    category: str  # Geopolitical, Economic, Defense, etc.
    level: RiskLevel
    score: float = Field(..., ge=0, le=100)
    trend: str = Field(..., description="up, down, stable")
    factors: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# Country-specific risk categories
RISK_CATEGORIES = [
    "Geopolitical",
    "Economic",
    "Defense",
    "Technology",
    "Climate",
    "Social",
    "Energy",
    "Health",
]

# Impact levels for world map visualization
IMPACT_LEVELS = {
    0-30: "low",
    31-60: "medium", 
    61-80: "high",
    81-100: "critical",
}
