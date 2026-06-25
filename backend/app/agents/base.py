from abc import ABC, abstractmethod
from typing import AsyncIterator, List
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid as _uuid

from app.memory.manager import memory_manager
from app.agents.llm_router import stream_response

logger = logging.getLogger(__name__)


class BaseAgent(ABC):

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def role_description(self) -> str: ...

    @property
    def allowed_tools(self) -> List[str]:
        return []

    @property
    def default_task_type(self) -> str:
        return "reasoning"

    @abstractmethod
    def build_system_prompt(self, context: dict) -> str: ...

    async def _save_message(self, db: AsyncSession, conversation_id: str, role: str, content: str):
        """Archive message to PostgreSQL for permanent history."""
        try:
            from app.memory.long_term import Message
            msg = Message(
                conversation_id=_uuid.UUID(conversation_id),
                role=role,
                content=content,
            )
            db.add(msg)
            await db.commit()
        except Exception as e:
            logger.warning(f"Message archive failed: {e}")

    async def run(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
    ) -> AsyncIterator[str]:

        # 1. Build context from memory
        context = await memory_manager.build_agent_context(
            db, user_id, conversation_id, user_message
        )

        # 2. Add user message to Redis session
        await memory_manager.add_message(user_id, conversation_id, "user", user_message)

        # 3. Archive user message to PostgreSQL
        await self._save_message(db, conversation_id, "user", user_message)

        # 4. Build system prompt with domain context
        system_prompt = self.build_system_prompt(context)

        # 5. Get full session history
        messages = await memory_manager.get_session_messages(user_id, conversation_id)

        # 6. Stream LLM response
        full_response = ""
        async for chunk in stream_response(
            system_prompt=system_prompt,
            messages=messages,
            task_type=self.default_task_type,
        ):
            full_response += chunk
            yield chunk

        # 7. Add assistant response to Redis session
        await memory_manager.add_message(user_id, conversation_id, "assistant", full_response)

        # 8. Archive assistant response to PostgreSQL
        await self._save_message(db, conversation_id, "assistant", full_response)

        # 9. Store in semantic memory for future context
        combined = f"User: {user_message}\nAssistant: {full_response}"
        await memory_manager.store_knowledge(
            user_id, combined, doc_type="conversation", source="agent"
        )

        logger.info(f"Agent [{self.name}] done | user={user_id[:8]} | chars={len(full_response)}")

    async def run_with_tools(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
    ) -> AsyncIterator[str]:
        """For MVP, delegates to run(). Tools to be added in next phase."""
        async for chunk in self.run(user_id, conversation_id, user_message, db):
            yield chunk
