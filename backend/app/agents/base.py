from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid as _uuid
import json

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
        return ["web_search", "generate_file", "send_email", "read_document"]

    @property
    def default_task_type(self) -> str:
        return "reasoning"

    @abstractmethod
    def build_system_prompt(self, context: dict) -> str: ...

    async def _save_message(self, db: AsyncSession, conversation_id: str, role: str, content: str):
        try:
            from datetime import datetime, timezone
            from sqlalchemy import update
            from app.memory.long_term import Message, Conversation
            msg = Message(
                conversation_id=_uuid.UUID(conversation_id),
                role=role,
                content=content,
            )
            db.add(msg)
            # Keep the conversation list sorted by real activity
            await db.execute(
                update(Conversation)
                .where(Conversation.id == _uuid.UUID(conversation_id))
                .values(updated_at=datetime.now(timezone.utc))
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Archive failed: {e}")

    async def _run_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return formatted result string."""
        try:
            from app.tools.registry import tool_registry
            result = await tool_registry.execute(tool_name, **tool_input)
            if not result.get("success"):
                return f"Tool {tool_name} failed: {result.get('error', 'Unknown error')}"

            data = result.get("result", {})

            # Web search — format results nicely
            if tool_name == "web_search":
                answer = data.get("answer", "")
                results = data.get("results", [])
                formatted = f"**Web Search Results for:** {data.get('query', '')}\n\n"
                if answer:
                    formatted += f"**Quick Answer:** {answer}\n\n"
                for i, r in enumerate(results[:3], 1):
                    formatted += f"**{i}. {r['title']}**\n{r['content'][:300]}\nSource: {r['url']}\n\n"
                return formatted

            # File generation — return special marker
            if tool_name == "generate_file":
                return json.dumps({
                    "__file__": True,
                    "filename": data.get("filename"),
                    "content_base64": data.get("content_base64"),
                    "mime_type": data.get("mime_type"),
                    "description": data.get("description"),
                    "rows_count": data.get("rows_count"),
                })

            return json.dumps(data)
        except Exception as e:
            return f"Tool error: {str(e)}"

    async def run(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
    ) -> AsyncIterator[str]:
        # 1. Build context
        context = await memory_manager.build_agent_context(
            db, user_id, conversation_id, user_message
        )

        # 2. Add to Redis + archive to PostgreSQL
        await memory_manager.add_message(user_id, conversation_id, "user", user_message)
        await self._save_message(db, conversation_id, "user", user_message)

        # 3. Build system prompt
        system_prompt = self.build_system_prompt(context)

        # 4. Get session history
        messages = await memory_manager.get_session_messages(user_id, conversation_id)

        # 5. Stream response
        full_response = ""
        async for chunk in stream_response(
            system_prompt=system_prompt,
            messages=messages,
            task_type=self.default_task_type,
        ):
            full_response += chunk
            yield chunk

        # 6. Save assistant response
        await memory_manager.add_message(user_id, conversation_id, "assistant", full_response)
        await self._save_message(db, conversation_id, "assistant", full_response)

        # 7. Semantic memory
        combined = f"User: {user_message}\nAssistant: {full_response}"
        await memory_manager.store_knowledge(
            user_id, combined, doc_type="conversation", source="agent"
        )

    async def run_with_tools(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
    ) -> AsyncIterator[str]:
        """Tool-enabled agent run — web search + file generation."""
        from app.agents.llm_router import get_tool_decision
        from app.tools.registry import tool_registry

        # 1. Build context
        context = await memory_manager.build_agent_context(
            db, user_id, conversation_id, user_message
        )

        await memory_manager.add_message(user_id, conversation_id, "user", user_message)
        await self._save_message(db, conversation_id, "user", user_message)

        system_prompt = self.build_system_prompt(context)
        messages = await memory_manager.get_session_messages(user_id, conversation_id)

        # 2. Check if tool needed
        tool_decision = await get_tool_decision(
            system_prompt=system_prompt,
            messages=messages,
            available_tools=self.allowed_tools,
        )

        tool_result_text = ""
        file_payload = None

        # 3. Execute tool if needed
        if tool_decision and tool_decision.get("tool"):
            tool_name = tool_decision["tool"]
            tool_input = tool_decision.get("input", {})
            yield f"\n*Using {tool_name}...*\n\n"

            raw_result = await self._run_tool(tool_name, tool_input)

            # Check if it's a file
            try:
                parsed = json.loads(raw_result)
                if parsed.get("__file__"):
                    file_payload = parsed
                    tool_result_text = (
                        f"File generated: {parsed['filename']} "
                        f"({parsed.get('rows_count',0)} rows)"
                    )
                else:
                    tool_result_text = raw_result
            except Exception:
                tool_result_text = raw_result

            # Add tool result to messages
            messages.append({"role": "user", "content": f"Tool result:\n{tool_result_text}"})

        # 4. Stream final response
        full_response = ""
        async for chunk in stream_response(
            system_prompt=system_prompt,
            messages=messages,
            task_type=self.default_task_type,
        ):
            full_response += chunk
            yield chunk

        # 5. If file was generated, emit download signal
        if file_payload:
            yield f"\n\n__FILE_DOWNLOAD__{json.dumps(file_payload)}__FILE_END__"

        # 6. Save
        await memory_manager.add_message(user_id, conversation_id, "assistant", full_response)
        await self._save_message(db, conversation_id, "assistant", full_response)
        combined = f"User: {user_message}\nAssistant: {full_response}"
        await memory_manager.store_knowledge(user_id, combined, doc_type="conversation", source="agent")
