from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

from app.memory.manager import memory_manager
from app.tools.registry import tool_registry
from app.agents.llm_router import stream_response

logger = logging.getLogger(__name__)


class BaseAgent(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def role_description(self) -> str:
        ...

    @property
    def allowed_tools(self) -> List[str]:
        return []

    @property
    def default_task_type(self) -> str:
        return "reasoning"

    @abstractmethod
    def build_system_prompt(self, context: dict) -> str:
        ...

    async def _archive_message(self, db: AsyncSession, conversation_id: str,
                               role: str, content: str):
        """Save a single message to PostgreSQL for permanent history."""
        try:
            import uuid as _uuid
            from app.memory.long_term import Message
            m = Message(
                conversation_id=_uuid.UUID(conversation_id),
                role=role,
                content=content,
            )
            db.add(m)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to archive message: {e}")

    async def run(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
    ) -> AsyncIterator[str]:

        # 1. Build memory context
        context = await memory_manager.build_agent_context(
            db, user_id, conversation_id, user_message
        )

        # 2. Add user message to short-term memory
        await memory_manager.add_message(
            user_id, conversation_id, "user", user_message
        )

        # 3. Archive user message to PostgreSQL
        await self._archive_message(db, conversation_id, "user", user_message)

        # 4. Build system prompt
        system_prompt = self.build_system_prompt(context)

        # 5. Get session messages
        messages = await memory_manager.get_session_messages(
            user_id, conversation_id
        )

        # 6. Stream response
        full_response = ""
        async for chunk in stream_response(
            system_prompt=system_prompt,
            messages=messages,
            task_type=self.default_task_type,
        ):
            full_response += chunk
            yield chunk

        # 7. Save assistant response to short-term memory
        await memory_manager.add_message(
            user_id, conversation_id, "assistant", full_response
        )

        # 8. Archive assistant message to PostgreSQL
        await self._archive_message(db, conversation_id, "assistant", full_response)

        # 9. Store in semantic memory
        combined = f"User: {user_message}\nAssistant: {full_response}"
        await memory_manager.store_knowledge(
            user_id, combined, doc_type="conversation", source="agent"
        )

        logger.info(
            f"Agent [{self.name}] completed | "
            f"user={user_id[:8]} | response_len={len(full_response)}"
        )

    async def run_with_tools(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
    ) -> AsyncIterator[str]:
        """Tool use version - for MVP uses simple run()."""
        async for chunk in self.run(
            user_id, conversation_id, user_message, db
        ):
            yield chunk
