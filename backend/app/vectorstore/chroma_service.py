"""
Chroma-backed vector store with in-memory fallback.
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional
from collections import deque

from openai import AsyncOpenAI

from app.config import settings

try:
    import chromadb  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    chromadb = None


# Maximum size for in-memory fallback to prevent unbounded memory growth
MAX_IN_MEMORY_DOCS = 1000


class ChromaService:
    """Optional vector store for GraphRAG context expansion."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.embedding_model = settings.openai_embedding_model
        self._in_memory_docs: List[Dict[str, Any]] = []
        self._collection = None

        if chromadb is not None:
            try:
                chroma_client = chromadb.Client()
                self._collection = chroma_client.get_or_create_collection(
                    name="geosynapse_context"
                )
            except Exception:
                self._collection = None

    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Add text documents for similarity retrieval."""
        if not texts:
            return 0

        metadatas = metadatas or [{} for _ in texts]
        embeddings = await self._embed_many(texts)
        ids = [str(uuid.uuid4()) for _ in texts]

        if self._collection is not None:
            try:
                self._collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings,
                )
                return len(texts)
            except Exception:
                pass

        # Add to in-memory fallback with LRU eviction
        for idx, text in enumerate(texts):
            new_doc = {
                "id": ids[idx],
                "text": text,
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
                "embedding": embeddings[idx],
            }
            
            # Simple LRU: if at capacity, remove oldest entries
            if len(self._in_memory_docs) >= MAX_IN_MEMORY_DOCS:
                # Remove oldest 10% of entries when at capacity
                remove_count = max(1, MAX_IN_MEMORY_DOCS // 10)
                self._in_memory_docs = self._in_memory_docs[remove_count:]
            
            self._in_memory_docs.append(new_doc)
        
        return len(texts)

    async def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k similar documents."""
        if not query:
            return []

        query_embedding = await self._embed_one(query)
        if not query_embedding:
            return []

        if self._collection is not None:
            try:
                response = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=max(k, 1),
                    include=["documents", "metadatas", "distances"],
                )
                docs = response.get("documents", [[]])[0]
                metas = response.get("metadatas", [[]])[0]
                distances = response.get("distances", [[]])[0]
                return [
                    {
                        "text": docs[i],
                        "metadata": metas[i] if i < len(metas) else {},
                        "score": 1 - float(distances[i]) if i < len(distances) else 0.0,
                    }
                    for i in range(min(len(docs), k))
                ]
            except Exception:
                pass

        scored = []
        for item in self._in_memory_docs:
            score = self._cosine_similarity(query_embedding, item["embedding"])
            scored.append(
                {
                    "text": item["text"],
                    "metadata": item.get("metadata", {}),
                    "score": score,
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    async def _embed_many(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=[text[:8000] for text in texts],
        )
        return [row.embedding for row in response.data]

    async def _embed_one(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text[:8000],
        )
        return response.data[0].embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


chroma_service = ChromaService()
