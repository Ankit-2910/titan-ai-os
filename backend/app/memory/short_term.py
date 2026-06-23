import json
import redis.asyncio as aioredis
from typing import Optional, List
from datetime import timedelta

from app.config import settings

SESSION_TTL_SECONDS = 60 * 60 * 2   # 2 hours of inactivity clears session


class ShortTermMemory:
    """
    Redis-backed in-session memory.
    Key pattern: titan:session:{user_id}:{conversation_id}
    Stores last N messages as a JSON list.
    """

    MAX_MESSAGES = 20   # keep only last 20 turns in short-term

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(settings.redis_url, decode_responses=True)
        return self._client

    def _key(self, user_id: str, conversation_id: str) -> str:
        return f"titan:session:{user_id}:{conversation_id}"

    async def add_message(self, user_id: str, conversation_id: str, role: str, content: str):
        """Append a message and reset the TTL."""
        client = await self._get_client()
        key = self._key(user_id, conversation_id)

        raw = await client.get(key)
        messages: List[dict] = json.loads(raw) if raw else []

        messages.append({"role": role, "content": content})

        # Keep only last MAX_MESSAGES
        if len(messages) > self.MAX_MESSAGES:
            messages = messages[-self.MAX_MESSAGES:]

        await client.setex(key, SESSION_TTL_SECONDS, json.dumps(messages))

    async def get_messages(self, user_id: str, conversation_id: str) -> List[dict]:
        """Return all messages for a session, newest-last."""
        client = await self._get_client()
        key = self._key(user_id, conversation_id)
        raw = await client.get(key)
        return json.loads(raw) if raw else []

    async def clear_session(self, user_id: str, conversation_id: str):
        """Delete a session from Redis."""
        client = await self._get_client()
        await client.delete(self._key(user_id, conversation_id))

    async def set_context_flag(self, user_id: str, key: str, value: str, ttl: int = 3600):
        """Store a temporary flag (e.g., 'awaiting_confirmation': 'true')."""
        client = await self._get_client()
        await client.setex(f"titan:flag:{user_id}:{key}", ttl, value)

    async def get_context_flag(self, user_id: str, key: str) -> Optional[str]:
        client = await self._get_client()
        return await client.get(f"titan:flag:{user_id}:{key}")


short_term_memory = ShortTermMemory()
