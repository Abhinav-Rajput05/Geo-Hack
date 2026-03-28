"""
GraphRAG Service - Knowledge Graph Augmented Generation
Combines Neo4j knowledge graph with LLM for intelligent question answering
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger
from app.config import settings
from app.ontology.ontology_service import ontology_service
from app.vectorstore import chroma_service
from app.database.postgres_client import postgres_client


class GraphRAGService:
    """Service for GraphRAG question answering"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/Geo-Hack",
                "X-Title": "Global Ontology Engine",
            }
        )
        self.model = settings.openai_model
        self.top_k = settings.graphrag_top_k
        self.max_hops = settings.graphrag_max_hops

    async def query(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Answer a question using GraphRAG"""
        normalized_question = (question or "").strip()
        if not normalized_question:
            return {
                "question": "",
                "answer": "Please provide a question.",
                "confidence": 0.0,
                "reasoning_chain": ["Input validation failed: empty question"],
                "supporting_facts": [],
                "related_entities": [],
                "relationships": [],
                "sources": [],
            }
        if len(normalized_question) > 2000:
            return {
                "question": normalized_question[:2000],
                "answer": "Your question is too long. Please keep it under 2000 characters.",
                "confidence": 0.0,
                "reasoning_chain": ["Input validation failed: question too long"],
                "supporting_facts": [],
                "related_entities": [],
                "relationships": [],
                "sources": [],
            }

        history = conversation_history or []
        effective_question = self._expand_question_with_history(normalized_question, history)

        # Step 1: Extract key entities from the question
        key_entities = await self._extract_key_entities(effective_question)

        # Step 2: Retrieve relevant subgraph from knowledge graph
        context_data = await self._retrieve_context(key_entities)

        # Step 2b: Retrieve similar semantic context from vector store
        try:
            vector_hits = await chroma_service.similarity_search(effective_question, k=self.top_k)
        except Exception:
            vector_hits = []
        context_data["vector_hits"] = self._filter_vector_hits(vector_hits, limit=self.top_k)

        # Step 2c: Retrieve structured evidence from PostgreSQL
        postgres_hits = await self._retrieve_structured_facts(
            effective_question,
            key_entities,
            limit=self.top_k,
        )
        context_data["postgres_hits"] = postgres_hits

        # Step 2d: Fuse context from graph + vector + postgres
        fused_context = self._fuse_context(context_data)
        context_data["fused_context"] = fused_context

        # Step 3: Generate answer using LLM with graph context
        if not fused_context:
            answer_data = {
                "answer": (
                    "I could not find enough retrieved evidence in the graph, vector index, or structured "
                    "database for this question. Please try a more specific query."
                ),
                "confidence": 0.1,
                "context_used": "No retrieval evidence available.",
                "supporting_facts": [],
                "sources": [],
            }
        else:
            answer_data = await self._generate_answer(
                normalized_question,
                context_data,
                conversation_history=history,
            )

        # Step 4: Build reasoning chain
        reasoning_chain = self._build_reasoning_chain(key_entities, context_data)

        sources = answer_data.get("sources", [])
        if not sources:
            sources = self._default_sources(context_data)

        confidence_value = self._normalize_confidence(answer_data.get("confidence"))

        supporting_facts = answer_data.get("supporting_facts", [])
        if not isinstance(supporting_facts, list):
            supporting_facts = []

        return {
            "question": normalized_question,
            "answer": answer_data["answer"],
            "confidence": confidence_value,
            "reasoning_chain": reasoning_chain,
            "supporting_facts": supporting_facts,
            "related_entities": context_data.get("entities", []),
            "relationships": context_data.get("relationships", []),
            "sources": sources,
            "context_used": answer_data.get("context_used", ""),
            "data_sources": sorted({source.get("type", "unknown") for source in sources}),
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
                    {
                        "role": "system",
                        "content": "Extract key entities from questions. Return only entity names.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            
            # FIXED: Safe JSON parsing with validation
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}, content: {content}")
                return []

            if isinstance(data, dict) and "entities" in data:
                return data["entities"]
            elif isinstance(data, list):
                return data
            else:
                # Try to extract any list value from the dict
                for v in data.values():
                    if isinstance(v, list):
                        return v
                logger.warning(f"Unexpected LLM response format: {type(data)}, keys: {list(data.keys())}")
                return []

        except Exception as e:
            logger.error(f"Error extracting entities: {e}", exc_info=True)
            return []

    async def _retrieve_context(self, entities: List[str]) -> Dict[str, Any]:
        """
        Retrieve context from knowledge graph.
        Parallelized entity and relationship lookups using asyncio.gather.
        Also does direct entity search for better recall.
        """
        entity_tasks = []
        relationship_tasks = []
        search_tasks = []

        for entity_name in entities:
            entity_tasks.append(
                ontology_service.get_related_entities(entity_name, limit=self.top_k)
            )
            relationship_tasks.append(
                ontology_service.get_relationships(entity_name, direction="both", limit=10)
            )
            # Also search by name directly for better recall
            search_tasks.append(
                ontology_service.search_entities(entity_name, limit=5)
            )

        try:
            entity_results = await asyncio.gather(*entity_tasks, return_exceptions=True)
            relationship_results = await asyncio.gather(*relationship_tasks, return_exceptions=True)
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error in parallel graph lookups: {e}", exc_info=True)
            entity_results = []
            relationship_results = []
            search_results = []

        all_entities = []
        all_relationships = []

        for idx, result in enumerate(entity_results):
            if isinstance(result, Exception):
                logger.warning(f"Entity lookup failed for '{entities[idx]}': {result}")
            elif result:
                all_entities.extend(result)

        # Add directly searched entities too
        for idx, result in enumerate(search_results):
            if isinstance(result, Exception):
                pass
            elif result:
                all_entities.extend(result)

        for idx, result in enumerate(relationship_results):
            if isinstance(result, Exception):
                logger.warning(f"Relationship lookup failed for '{entities[idx]}': {result}")
            elif result:
                all_relationships.extend(result)

        # Deduplicate entities by name
        seen_names = set()
        unique_entities = []
        for e in all_entities:
            name = e.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                unique_entities.append(e)

        subgraph = {}
        if entities:
            try:
                subgraph = await ontology_service.get_entity_subgraph(
                    entities[0], depth=self.max_hops, limit=50
                )
            except Exception as exc:
                logger.warning(f"Graph context subgraph lookup failed for '{entities[0]}': {exc}")
                subgraph = {}

        return {
            "entities": unique_entities[:20],
            "relationships": all_relationships[:20],
            "subgraph": subgraph,
        }

    async def _retrieve_structured_facts(
        self,
        question: str,
        entities: List[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve structured facts from PostgreSQL articles."""
        patterns: List[str] = []
        trimmed_question = (question or "").strip()
        if trimmed_question:
            patterns.append(f"%{trimmed_question[:180]}%")

        for entity in entities[:4]:
            ent = (entity or "").strip()
            if ent:
                patterns.append(f"%{ent[:120]}%")
                # Also add individual words from entity name for better recall
                for word in ent.split():
                    if len(word) > 4:
                        patterns.append(f"%{word}%")

        if not patterns:
            return []

        collected: Dict[str, Dict[str, Any]] = {}
        for pattern in patterns:
            try:
                rows = await postgres_client.execute_query(
                    """
                    SELECT id, title, summary, source, url, published_at, domain, region
                    FROM articles
                    WHERE title ILIKE :pattern
                       OR summary ILIKE :pattern
                       OR content ILIKE :pattern
                    ORDER BY published_at DESC
                    LIMIT :limit
                    """,
                    {"pattern": pattern, "limit": max(1, min(limit, 15))},
                )
            except Exception as exc:
                logger.warning(f"PostgreSQL retrieval skipped: {exc}")
                return []

            for row in rows:
                key = str(row.get("url") or row.get("id") or "")
                if not key:
                    continue
                title = str(row.get("title") or "")
                summary = str(row.get("summary") or "")
                text = (title + " " + summary).strip()
                lexical = self._keyword_overlap_score(question, text)
                if key not in collected or lexical > float(collected[key].get("score", 0.0)):
                    collected[key] = {
                        "id": row.get("id"),
                        "text": f"{title}. {summary}".strip(". "),
                        "metadata": {
                            "source": row.get("source", "postgres"),
                            "url": row.get("url", ""),
                            "domain": row.get("domain"),
                            "region": row.get("region"),
                            "published_at": str(row.get("published_at") or ""),
                        },
                        "score": round(0.35 + 0.65 * lexical, 4),
                    }

        hits = sorted(collected.values(), key=lambda item: item.get("score", 0.0), reverse=True)
        return hits[: max(1, limit)]

    def _filter_vector_hits(self, vector_hits: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for hit in vector_hits or []:
            score = float(hit.get("score", 0.0) or 0.0)
            # Filter noisy matches that often degrade answer quality.
            if score < 0.08:
                continue
            filtered.append(
                {
                    "text": str(hit.get("text", "")),
                    "metadata": hit.get("metadata", {}) or {},
                    "score": round(score, 4),
                }
            )
        filtered.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return filtered[: max(1, limit)]

    def _fuse_context(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Merge graph, vector, and structured DB evidence into ranked context."""
        fused: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for hit in context_data.get("vector_hits", []) or []:
            text = str(hit.get("text", "")).strip()
            if not text:
                continue
            key = text.lower()[:220]
            if key in seen:
                continue
            seen.add(key)
            fused.append(
                {
                    "type": "vector",
                    "text": text[:350],
                    "score": float(hit.get("score", 0.0) or 0.0),
                    "metadata": hit.get("metadata", {}) or {},
                }
            )

        for hit in context_data.get("postgres_hits", []) or []:
            text = str(hit.get("text", "")).strip()
            if not text:
                continue
            key = text.lower()[:220]
            if key in seen:
                continue
            seen.add(key)
            fused.append(
                {
                    "type": "postgres",
                    "text": text[:350],
                    "score": float(hit.get("score", 0.0) or 0.0),
                    "metadata": hit.get("metadata", {}) or {},
                }
            )

        for entity in (context_data.get("entities", []) or [])[:12]:
            name = str(entity.get("name", "")).strip()
            entity_type = str(entity.get("type", "Unknown")).strip()
            if not name:
                continue
            text = f"{name} ({entity_type})"
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            fused.append(
                {
                    "type": "graph_entity",
                    "text": text,
                    "score": float(entity.get("confidence", 0.66) or 0.66),
                    "metadata": {"entity_type": entity_type},
                }
            )

        for rel in (context_data.get("relationships", []) or [])[:12]:
            src = (rel.get("source") or {}).get("name", "?")
            dst = (rel.get("target") or {}).get("name", "?")
            rel_type = rel.get("type", "related_to")
            text = f"{src} -[{rel_type}]-> {dst}"
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            rel_conf = float((rel.get("properties") or {}).get("confidence", 0.62) or 0.62)
            fused.append(
                {
                    "type": "graph_relationship",
                    "text": text,
                    "score": rel_conf,
                    "metadata": {"relationship_type": rel_type},
                }
            )

        fused.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return fused[:24]

    async def _generate_answer(
        self,
        question: str,
        context_data: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Generate answer using LLM with graph context"""

        # Build context from fused retrieval data.
        fused_context = context_data.get("fused_context", []) or []
        context_lines: List[str] = []
        for idx, item in enumerate(fused_context[:16], start=1):
            context_lines.append(
                f"{idx}. [{item.get('type', 'unknown')}] {item.get('text', '')} "
                f"(score={round(float(item.get('score', 0.0) or 0.0), 3)})"
            )
        context = "\n".join(context_lines) if context_lines else "No retrieved context available."

        history_text = self._render_history(conversation_history or [])
        prompt = f"""Use the retrieved context and conversation history to answer the user question.
Prioritize retrieved evidence from graph, vector, and PostgreSQL.
If evidence is weak or missing, explicitly say what is unknown and do not invent facts.

CONVERSATION HISTORY:
{history_text}

RETRIEVED CONTEXT:
{context}

QUESTION: {question}

Provide your answer in JSON format with:
{{
  "answer": "Clear user-friendly explanation",
  "context_used": "Short summary of which context sources were used and why",
  "confidence": "high|medium|low",
  "supporting_facts": [
    {{"entity": "entity name", "relation": "relationship", "target": "target", "source": "source"}}
  ],
  "sources": [
    {{"type": "graph|vector|postgres", "reference": "source identifier", "score": 0.0-1.0}}
  ]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an intelligent assistant that answers user queries using retrieved "
                            "knowledge from graph data, vector search, and structured PostgreSQL records. "
                            "Always provide clear, context-aware, and well-structured answers. "
                            "Do not hallucinate. If context is insufficient, state limitations explicitly."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=settings.openai_max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            
            # FIXED: Safe JSON parsing with validation
            try:
                payload = json.loads(content)
                if not isinstance(payload, dict):
                    return self._safe_generation_fallback()
                return {
                    "answer": str(payload.get("answer", "")).strip()
                    or "I could not generate a reliable answer from retrieved context.",
                    "confidence": payload.get("confidence", "low"),
                    "context_used": str(payload.get("context_used", "")).strip(),
                    "supporting_facts": payload.get("supporting_facts", []),
                    "sources": payload.get("sources", []),
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM answer JSON: {e}, content: {content}")
                return self._safe_generation_fallback()

        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return self._safe_generation_fallback()

    def _expand_question_with_history(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        if not conversation_history:
            return question
        tail = conversation_history[-4:]
        snippets: List[str] = []
        for item in tail:
            role = (item.get("role") or "user").strip().lower()
            content = (item.get("content") or "").strip()
            if not content:
                continue
            snippets.append(f"{role}: {content}")
        if not snippets:
            return question
        return f"Conversation context:\n" + "\n".join(snippets) + f"\n\nCurrent question: {question}"

    def _render_history(self, conversation_history: List[Dict[str, str]]) -> str:
        if not conversation_history:
            return "No prior conversation."
        lines: List[str] = []
        for item in conversation_history[-6:]:
            role = (item.get("role") or "user").strip().lower()
            content = (item.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else "No prior conversation."

    def _build_reasoning_chain(
        self, entities: List[str], context_data: Dict[str, Any]
    ) -> List[str]:
        """Build reasoning chain for transparency"""

        chain = []

        # Step 1: Entity identification
        if entities:
            chain.append(f"Identified key entities: {', '.join(entities)}")

        # Step 2: Graph traversal
        entity_count = len(context_data.get("entities", []))
        rel_count = len(context_data.get("relationships", []))
        chain.append(
            f"Traversed knowledge graph: found {entity_count} related entities and {rel_count} relationships"
        )

        # Step 3: Context synthesis
        if entity_count > 0:
            chain.append("Synthesized context from entity relationships")
        else:
            chain.append("No graph data found, using general knowledge")

        vector_hits = len(context_data.get("vector_hits", []))
        chain.append(f"Retrieved {vector_hits} semantic matches from vector context")

        postgres_hits = len(context_data.get("postgres_hits", []))
        chain.append(f"Retrieved {postgres_hits} structured records from PostgreSQL")

        # Step 4: Answer generation
        fused_hits = len(context_data.get("fused_context", []))
        chain.append(f"Fused and ranked {fused_hits} evidence items across graph/vector/postgres")
        chain.append("Generated answer using LLM with fused retrieval context")

        return chain

    def _safe_generation_fallback(self) -> Dict[str, Any]:
        return {
            "answer": "I encountered an error while processing your question. Please try again.",
            "confidence": "low",
            "context_used": "Generation fallback after retrieval/parsing error.",
            "supporting_facts": [],
            "sources": [],
        }

    def _normalize_confidence(self, confidence: Any) -> float:
        if isinstance(confidence, (int, float)):
            return max(0.0, min(float(confidence), 1.0))
        label = str(confidence or "").strip().lower()
        if label == "high":
            return 0.85
        if label == "medium":
            return 0.6
        if label == "low":
            return 0.3
        return 0.0

    def _keyword_overlap_score(self, question: str, text: str) -> float:
        q_tokens = {t.strip(".,:;!?()[]{}").lower() for t in question.split() if len(t.strip()) >= 3}
        t_tokens = {t.strip(".,:;!?()[]{}").lower() for t in text.split() if len(t.strip()) >= 3}
        if not q_tokens or not t_tokens:
            return 0.0
        overlap = len(q_tokens.intersection(t_tokens))
        return overlap / max(1, len(q_tokens))

    def _default_sources(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []
        for hit in context_data.get("vector_hits", []) or []:
            sources.append(
                {
                    "type": "vector",
                    "reference": (hit.get("metadata") or {}).get("url")
                    or (hit.get("metadata") or {}).get("source", "vector_context"),
                    "score": float(hit.get("score", 0.0) or 0.0),
                }
            )
        for hit in context_data.get("postgres_hits", []) or []:
            sources.append(
                {
                    "type": "postgres",
                    "reference": (hit.get("metadata") or {}).get("url")
                    or (hit.get("metadata") or {}).get("source", "postgres_articles"),
                    "score": float(hit.get("score", 0.0) or 0.0),
                }
            )
        for rel in (context_data.get("relationships", []) or [])[:8]:
            src = (rel.get("source") or {}).get("name", "?")
            dst = (rel.get("target") or {}).get("name", "?")
            sources.append(
                {
                    "type": "graph",
                    "reference": f"{src}->{dst}",
                    "score": float((rel.get("properties") or {}).get("confidence", 0.62) or 0.62),
                }
            )
        return sources[:18]


# Singleton instance
graphrag_service = GraphRAGService()
