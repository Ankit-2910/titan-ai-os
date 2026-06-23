from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.memory.short_term import short_term_memory
from app.memory.long_term import long_term_memory
from app.memory.semantic import semantic_memory


class MemoryManager:
    """
    Single entry point for all memory operations.
    The agent calls this — it handles which tier to use.

    Tiers:
      Short-term  →  Redis  (current session, last 20 messages, TTL 2h)
      Long-term   →  PostgreSQL (facts about user, archived conversations)
      Semantic    →  Qdrant (document embeddings, knowledge search)
    """

    # ── Short-Term ────────────────────────────────────────────────────────────

    async def add_message(self, user_id: str, conversation_id: str, role: str, content: str):
        await short_term_memory.add_message(user_id, conversation_id, role, content)

    async def get_session_messages(self, user_id: str, conversation_id: str) -> List[dict]:
        return await short_term_memory.get_messages(user_id, conversation_id)

    async def clear_session(self, user_id: str, conversation_id: str):
        await short_term_memory.clear_session(user_id, conversation_id)

    # ── Long-Term ─────────────────────────────────────────────────────────────

    async def save_user_fact(self, db: AsyncSession, user_id: str,
                             category: str, key: str, value: str):
        await long_term_memory.save_fact(db, user_id, category, key, value)

    async def get_user_facts_text(self, db: AsyncSession, user_id: str) -> str:
        return await long_term_memory.get_facts_as_text(db, user_id)

    async def create_conversation(self, db: AsyncSession, user_id: str,
                                  title: Optional[str] = None):
        return await long_term_memory.create_conversation(db, user_id, title)

    async def archive_session(self, db: AsyncSession, user_id: str, conversation_id: str):
        """Move Redis messages to PostgreSQL for permanent storage."""
        messages = await short_term_memory.get_messages(user_id, conversation_id)
        if messages:
            await long_term_memory.archive_messages(db, conversation_id, messages)

    # ── Semantic ──────────────────────────────────────────────────────────────

    async def store_knowledge(self, user_id: str, content: str,
                              doc_type: str = "general", source: str = "user"):
        await semantic_memory.store(user_id, content, doc_type, source)

    async def search_knowledge(self, user_id: str, query: str,
                               limit: int = 5) -> List[dict]:
        return await semantic_memory.search(user_id, query, limit=limit)

    # ── Context Builder ───────────────────────────────────────────────────────

    async def build_agent_context(self, db: AsyncSession,
                                  user_id: str, conversation_id: str,
                                  current_query: str) -> dict:
        """
        Assembles all memory tiers into a single context dict for the agent.
        Called once at the start of each agent turn.
        """
        session_messages = await self.get_session_messages(user_id, conversation_id)
        user_facts = await self.get_user_facts_text(db, user_id)
        relevant_knowledge = await self.search_knowledge(user_id, current_query, limit=3)

        return {
            "session_messages": session_messages,
            "user_facts": user_facts,
            "relevant_knowledge": relevant_knowledge,
        }


memory_manager = MemoryManager()
