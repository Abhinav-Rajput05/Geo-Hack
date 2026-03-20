"""
NLP Service - Entity Extraction, Relation Extraction, and Sentiment Analysis
"""
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings


class NLPService:
    """Service for NLP operations using OpenAI"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text using GPT-4"""
        
        prompt = f"""Extract named entities from the following text. 
For each entity, identify:
1. name: The entity name
2. type: The entity type (Country, Organization, Company, Individual, System, Event, Location, Resource)
3. category: The domain category (Geopolitical, Economic, Defense, Technology, Climate, Energy, Health, Social)

Return a JSON array of entities found.

Text:
{text[:3000]}  # Limit text length

Expected output format:
[
  {{"name": "entity name", "type": "type", "category": "category"}},
  ...
]"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert entity extraction system. Extract entities and categorize them accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            entities = json.loads(content)
            
            # Ensure it's a list
            if isinstance(entities, dict) and 'entities' in entities:
                entities = entities['entities']
            
            return entities if isinstance(entities, list) else []
            
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return []
    
    async def extract_relations(
        self, 
        text: str, 
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities"""
        
        entity_names = [e['name'] for e in entities]
        
        prompt = f"""Extract relationships between the following entities in the text.
Identify:
1. source: The source entity name
2. target: The target entity name  
3. type: Relationship type (alliesWith, tradesWith, sanctions, supplies, dependsOn, competesWith, influences, threatens, memberOf, leads, owns)
4. properties: Any additional details about the relationship

Entities found: {', '.join(entity_names)}

Text:
{text[:3000]}

Expected output format:
[
  {{"source": "entity1", "target": "entity2", "type": "relationshipType", "properties": {{}}}},
  ...
]"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert relationship extraction system. Identify relationships between entities accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            relations = json.loads(content)
            
            if isinstance(relations, dict) and 'relations' in relations:
                relations = relations['relations']
            
            return relations if isinstance(relations, list) else []
            
        except Exception as e:
            print(f"Error extracting relations: {e}")
            return []
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        
        prompt = f"""Analyze the sentiment of the following text.
Return a JSON object with:
1. sentiment: positive, negative, or neutral
2. score: A score from -1 (very negative) to 1 (very positive)
3. confidence: Confidence level from 0 to 1

Text:
{text[:2000]}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a sentiment analysis system. Analyze text sentiment accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.0}
    
    async def process_article(
        self, 
        article: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process article: extract entities, relations, sentiment"""
        
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        
        # Extract entities
        entities = await self.extract_entities(text)
        
        # Extract relations
        relations = await self.extract_relations(text, entities)
        
        # Analyze sentiment
        sentiment = await self.analyze_sentiment(text)
        
        return {
            'article_id': article.get('id'),
            'entities': entities,
            'relations': relations,
            'sentiment': sentiment,
            'processed_at': 'timestamp',
        }
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding using OpenAI"""
        
        try:
            response = await self.client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text[:8000]  # Limit input length
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []


# Singleton instance
nlp_service = NLPService()
