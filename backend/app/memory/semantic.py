from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue
)
from typing import List, Optional, Dict, Any
import uuid
import hashlib

from app.config import settings

COLLECTION_NAME = "titan_knowledge"
VECTOR_SIZE = 384


class SemanticMemory:

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            if settings.qdrant_api_key:
                self._client = AsyncQdrantClient(
                    url=settings.qdrant_host,
                    api_key=settings.qdrant_api_key,
                )
            else:
                self._client = AsyncQdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                )
        return self._client

    def _embed(self, text: str) -> List[float]:
        vector = []
        for i in range(VECTOR_SIZE):
            h = hashlib.sha256(
                f"{i}:{text[:100]}".encode()
            ).digest()
            val = (h[i % 32] / 255.0) * 2 - 1
            vector.append(val)
        return vector

    def _make_point_id(self, user_id: str, content: str) -> str:
        h = hashlib.sha256(
            f"{user_id}:{content[:200]}".encode()
        ).hexdigest()
        return str(uuid.UUID(h[:32]))

    async def ensure_collection(self):
        try:
            client = await self._get_client()
            collections = await client.get_collections()
            names = [c.name for c in collections.collections]
            if COLLECTION_NAME not in names:
                await client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE
                    ),
                )
        except Exception:
            pass

    async def store(self, user_id: str, content: str,
                    doc_type: str = "general",
                    source: str = "user",
                    metadata: Optional[Dict[str, Any]] = None):
        try:
            await self.ensure_collection()
            client = await self._get_client()
            vector = self._embed(content)
            point_id = self._make_point_id(user_id, content)
            payload = {
                "user_id": user_id,
                "content": content,
                "doc_type": doc_type,
                "source": source,
                **(metadata or {}),
            }
            await client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )],
            )
            return point_id
        except Exception:
            return None

    async def search(self, user_id: str, query: str,
                     limit: int = 5,
                     doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            await self.ensure_collection()
            client = await self._get_client()
            query_vector = self._embed(query)
            must_conditions = [
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
            if doc_type:
                must_conditions.append(
                    FieldCondition(
                        key="doc_type",
                        match=MatchValue(value=doc_type)
                    )
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
        except Exception:
            return []

    async def delete_by_user(self, user_id: str):
        try:
            client = await self._get_client()
            await client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(
                    must=[FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )]
                ),
            )
        except Exception:
            pass


semantic_memory = SemanticMemory()