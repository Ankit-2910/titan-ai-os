from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, SearchRequest
)
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
import uuid
import hashlib

from app.config import settings

COLLECTION_NAME = "titan_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # 384 dimensions, fast, free, local
VECTOR_SIZE = 384


class SemanticMemory:
    """
    Qdrant-backed semantic memory.
    Stores: user documents, web search results, extracted facts, past decisions.
    Each point has: vector + payload (text, user_id, source, doc_type, created_at)
    """

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self._embedder: Optional[SentenceTransformer] = None

    def _get_embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        return self._embedder

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            kwargs = {"host": settings.qdrant_host, "port": settings.qdrant_port}
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
                kwargs["https"] = True
            self._client = AsyncQdrantClient(**kwargs)
        return self._client

    def _embed(self, text: str) -> List[float]:
        """Convert text to a 384-dim embedding vector."""
        embedder = self._get_embedder()
        return embedder.encode(text, normalize_embeddings=True).tolist()

    async def ensure_collection(self):
        """Create the Qdrant collection if it doesn't exist."""
        client = await self._get_client()
        collections = await client.get_collections()
        names = [c.name for c in collections.collections]

        if COLLECTION_NAME not in names:
            await client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    def _make_point_id(self, user_id: str, content: str) -> str:
        """Deterministic UUID from user_id + content hash — prevents duplicates."""
        h = hashlib.sha256(f"{user_id}:{content[:200]}".encode()).hexdigest()
        return str(uuid.UUID(h[:32]))

    async def store(self, user_id: str, content: str, doc_type: str = "general",
                    source: str = "user", metadata: Optional[Dict[str, Any]] = None):
        """Embed and store a text chunk in Qdrant."""
        await self.ensure_collection()
        client = await self._get_client()

        vector = self._embed(content)
        point_id = self._make_point_id(user_id, content)

        payload = {
            "user_id": user_id,
            "content": content,
            "doc_type": doc_type,    # "document" | "search_result" | "fact" | "decision"
            "source": source,
            **(metadata or {}),
        }

        await client.upsert(
            collection_name=COLLECTION_NAME,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    async def search(self, user_id: str, query: str, limit: int = 5,
                     doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for semantically similar content scoped to a specific user."""
        await self.ensure_collection()
        client = await self._get_client()

        query_vector = self._embed(query)

        # Filter by user_id (and optionally doc_type)
        must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        if doc_type:
            must_conditions.append(
                FieldCondition(key="doc_type", match=MatchValue(value=doc_type))
            )

        results = await client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions),
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "id": str(r.id),
                "score": round(r.score, 4),
                "content": r.payload.get("content", ""),
                "doc_type": r.payload.get("doc_type", ""),
                "source": r.payload.get("source", ""),
            }
            for r in results
        ]

    async def delete_by_user(self, user_id: str):
        """Delete all vectors for a user (GDPR/account deletion)."""
        client = await self._get_client()
        await client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
        )


semantic_memory = SemanticMemory()
