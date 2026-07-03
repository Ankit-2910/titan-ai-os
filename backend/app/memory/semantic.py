import logging
import math
import uuid
import hashlib
from typing import List, Optional, Dict, Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, PayloadSchemaType
)
from google import genai
from google.genai import types as genai_types

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "titan_knowledge"
VECTOR_SIZE = 384
EMBED_MODEL = "gemini-embedding-001"


class SemanticMemory:

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self._genai_client: Optional[genai.Client] = None
        self._collection_ready = False

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

    def _get_genai_client(self) -> genai.Client:
        if self._genai_client is None:
            self._genai_client = genai.Client(api_key=settings.gemini_api_key)
        return self._genai_client

    async def _embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """Real semantic embedding via Gemini, truncated to VECTOR_SIZE and re-normalized."""
        client = self._get_genai_client()
        result = await client.aio.models.embed_content(
            model=EMBED_MODEL,
            contents=text[:8000],
            config=genai_types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=VECTOR_SIZE,
            ),
        )
        vector = list(result.embeddings[0].values)
        # Truncated Gemini embeddings are not unit-length; normalize for cosine distance
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def _make_point_id(self, user_id: str, content: str) -> str:
        h = hashlib.sha256(
            f"{user_id}:{content[:200]}".encode()
        ).hexdigest()
        return str(uuid.UUID(h[:32]))

    async def ensure_collection(self):
        if self._collection_ready:
            return
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
            # Qdrant Cloud requires payload indexes for filtered fields
            for field in ("user_id", "doc_type"):
                try:
                    await client.create_payload_index(
                        collection_name=COLLECTION_NAME,
                        field_name=field,
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    pass  # index already exists
            self._collection_ready = True
        except Exception as e:
            logger.warning(f"Qdrant ensure_collection failed: {e}")

    async def store(self, user_id: str, content: str,
                    doc_type: str = "general",
                    source: str = "user",
                    metadata: Optional[Dict[str, Any]] = None):
        try:
            await self.ensure_collection()
            client = await self._get_client()
            vector = await self._embed(content, task_type="RETRIEVAL_DOCUMENT")
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
        except Exception as e:
            logger.warning(f"Semantic store failed: {e}")
            return None

    async def search(self, user_id: str, query: str,
                     limit: int = 5,
                     doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            await self.ensure_collection()
            client = await self._get_client()
            query_vector = await self._embed(query, task_type="RETRIEVAL_QUERY")
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
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def delete_by_user(self, user_id: str):
        try:
            await self.ensure_collection()
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
        except Exception as e:
            logger.warning(f"Semantic delete failed: {e}")


semantic_memory = SemanticMemory()
