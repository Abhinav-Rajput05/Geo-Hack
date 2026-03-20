"""
GraphRAG Service - Knowledge Graph Augmented Generation
Combines Neo4j knowledge graph with LLM for intelligent question answering
"""
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.ontology.ontology_service import ontology_service


class GraphRAGService:
    """Service for GraphRAG question answering"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.top_k = settings.graphrag_top_k
        self.max_hops = settings.graphrag_max_hops
    
    async def query(self, question: str) -> Dict[str, Any]:
        """Answer a question using GraphRAG"""
        
        # Step 1: Extract key entities from the question
        key_entities = await self._extract_key_entities(question)
        
        # Step 2: Retrieve relevant subgraph from knowledge graph
        context_data = await self._retrieve_context(key_entities)
        
        # Step 3: Generate answer using LLM with graph context
        answer_data = await self._generate_answer(question, context_data)
        
        # Step 4: Build reasoning chain
        reasoning_chain = self._build_reasoning_chain(key_entities, context_data)
        
        return {
            'question': question,
            'answer': answer_data['answer'],
            'confidence': answer_data['confidence'],
            'reasoning_chain': reasoning_chain,
            'supporting_facts': answer_data['supporting_facts'],
            'related_entities': context_data.get('entities', []),
        }
    
    async def _extract_key_entities(self, question: str) -> List[str]:
        """Extract key entities from the question"""
        
        prompt = f"""Extract the key entities (countries, organizations, people, topics) from this question.
Return a JSON array of entity names.

Question: {question}

Example output: ["United States", "NATO", "China"]"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract key entities from questions. Return only entity names."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            if isinstance(data, dict) and 'entities' in data:
                return data['entities']
            elif isinstance(data, list):
                return data
            else:
                return []
                
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return []
    
    async def _retrieve_context(self, entities: List[str]) -> Dict[str, Any]:
        """Retrieve context from knowledge graph"""
        
        all_entities = []
        all_relationships = []
        
        for entity_name in entities:
            # Get related entities
            related = await ontology_service.get_related_entities(
                entity_name, 
                limit=self.top_k
            )
            all_entities.extend(related)
            
            # Get relationships
            rels = await ontology_service.get_relationships(
                entity_name,
                direction="both",
                limit=10
            )
            all_relationships.extend(rels)
        
        # Get subgraph for first entity if available
        subgraph = {}
        if entities:
            subgraph = await ontology_service.get_entity_subgraph(
                entities[0],
                depth=self.max_hops,
                limit=50
            )
        
        return {
            'entities': all_entities[:20],  # Limit context size
            'relationships': all_relationships[:20],
            'subgraph': subgraph,
        }
    
    async def _generate_answer(
        self, 
        question: str, 
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate answer using LLM with graph context"""
        
        # Build context from retrieved data
        context_parts = []
        
        # Add entity information
        if context_data.get('entities'):
            entity_info = "\n".join([
                f"- {e.get('name')}: {e.get('type', 'Unknown')}"
                for e in context_data['entities'][:10]
            ])
            context_parts.append(f"Entities:\n{entity_info}")
        
        # Add relationship information
        if context_data.get('relationships'):
            rel_info = "\n".join([
                f"- {r.get('source', {}).get('name', '?')} {r.get('type', 'related')} {r.get('target', {}).get('name', '?')}"
                for r in context_data['relationships'][:10]
            ])
            context_parts.append(f"Relationships:\n{rel_info}")
        
        context = "\n\n".join(context_parts) if context_parts else "No relevant data found in knowledge graph."
        
        prompt = f"""You are an expert analyst with access to a global knowledge graph.
Use the following context from the knowledge graph to answer the question.
If the context doesn't contain enough information, provide your best answer based on general knowledge
and clearly indicate any assumptions.

KNOWLEDGE GRAPH CONTEXT:
{context}

QUESTION: {question}

Provide your answer in JSON format with:
{{
  "answer": "Your detailed answer",
  "confidence": 0.0-1.0,
  "supporting_facts": [
    {{"entity": "entity name", "relation": "relationship", "target": "target", "source": "source"}}
  ]
}}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a knowledgeable analyst. Answer questions accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=settings.openai_max_tokens,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"Error generating answer: {e}")
            return {
                'answer': 'I encountered an error while processing your question. Please try again.',
                'confidence': 0.0,
                'supporting_facts': []
            }
    
    def _build_reasoning_chain(
        self, 
        entities: List[str], 
        context_data: Dict[str, Any]
    ) -> List[str]:
        """Build reasoning chain for transparency"""
        
        chain = []
        
        # Step 1: Entity identification
        if entities:
            chain.append(f"Identified key entities: {', '.join(entities)}")
        
        # Step 2: Graph traversal
        entity_count = len(context_data.get('entities', []))
        rel_count = len(context_data.get('relationships', []))
        chain.append(f"Traversed knowledge graph: found {entity_count} related entities and {rel_count} relationships")
        
        # Step 3: Context synthesis
        if entity_count > 0:
            chain.append("Synthesized context from entity relationships")
        else:
            chain.append("No graph data found, using general knowledge")
        
        # Step 4: Answer generation
        chain.append("Generated answer using LLM with graph context")
        
        return chain


# Singleton instance
graphrag_service = GraphRAGService()
