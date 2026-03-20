"""
Ontology Module
"""
from app.ontology.schema import (
    Entity, EntityType, 
    Relationship, RelationshipType,
    RiskAssessment, RiskLevel,
    ENTITY_PROPERTIES, RELATIONSHIP_PROPERTIES,
    RISK_CATEGORIES
)
from app.ontology.ontology_service import ontology_service, OntologyService

__all__ = [
    'Entity', 'EntityType',
    'Relationship', 'RelationshipType',
    'RiskAssessment', 'RiskLevel',
    'ENTITY_PROPERTIES', 'RELATIONSHIP_PROPERTIES',
    'RISK_CATEGORIES',
    'ontology_service', 'OntologyService'
]
