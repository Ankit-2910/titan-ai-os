from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, AsyncIterator
import uuid
import json
import asyncio

from app.db import get_db
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.memory.manager import memory_manager
from app.agents.executive import executive_agent
from app.tools.registry import tool_registry
from app.tools.web_search import WebSearchTool
from app.tools.email_send import EmailSendTool
from app.tools.doc_reader import DocReaderTool

router = APIRouter()

# ─── Register tools on startup ────────────────────────────────────────────────
tool_registry.register(WebSearchTool())
tool_registry.register(EmailSendTool())
tool_registry.register(DocReaderTool())


# ─── Request / Response Schemas ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None   # None = start new conversation
    use_tools: bool = True                   # False = simple streaming, no tool use
    file_content_base64: Optional[str] = None
    file_type: Optional[str] = None
    filename: Optional[str] = None


class ConversationResponse(BaseModel):
    conversation_id: str
    title: Optional[str] = None


# ─── SSE Helpers ──────────────────────────────────────────────────────────────

def sse_event(data: str, event: str = "message") -> str:
    """Format a Server-Sent Event string."""
    # Escape newlines so the SSE frame stays valid
    data_escaped = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {data_escaped}\n\n"


async def stream_agent_response(
    user_id: str,
    conversation_id: str,
    message: str,
    db: AsyncSession,
    use_tools: bool,
) -> AsyncIterator[str]:
    """Wrap the agent's async iterator and format as SSE events."""
    try:
        # Yield start event
        yield sse_event(json.dumps({"type": "start", "conversation_id": conversation_id}), "control")

        agent_iter = (
            executive_agent.run_with_tools(user_id, conversation_id, message, db)
            if use_tools
            else executive_agent.run(user_id, conversation_id, message, db)
        )

        async for chunk in agent_iter:
            if chunk:
                yield sse_event(json.dumps({"type": "chunk", "text": chunk}))

        # Yield done event
        yield sse_event(json.dumps({"type": "done"}), "control")

    except asyncio.CancelledError:
        # Client disconnected — clean exit
        return
    except Exception as e:
        yield sse_event(json.dumps({"type": "error", "message": str(e)}), "control")


# ─── POST /chat ───────────────────────────────────────────────────────────────

@router.post("/")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint. Returns a Server-Sent Event stream.
    
    - If conversation_id is None, a new conversation is created.
    - If a file is attached, it's read first and prepended to the message.
    - Streams response chunks as SSE events.
    """
    user_id = str(current_user.id)

    # ── Create or validate conversation ──────────────────────────────────────
    if not body.conversation_id:
        # New conversation — create DB record
        first_words = " ".join(body.message.split()[:6])
        conv = await memory_manager.create_conversation(
            db, user_id, title=f"{first_words}..."
        )
        conversation_id = str(conv.id)
    else:
        conversation_id = body.conversation_id

    # ── Handle file attachment ────────────────────────────────────────────────
    message = body.message
    if body.file_content_base64 and body.file_type:
        doc_result = await tool_registry.execute(
            "read_document",
            file_content_base64=body.file_content_base64,
            file_type=body.file_type,
            filename=body.filename or "uploaded_document",
        )
        if doc_result["success"]:
            extracted_text = doc_result["result"]["text"]
            filename = doc_result["result"]["filename"]
            message = (
                f"{body.message}\n\n"
                f"[Attached document: {filename}]\n"
                f"{extracted_text}"
            )
            # Also store in semantic memory for future searches
            await memory_manager.store_knowledge(
                user_id, extracted_text,
                doc_type="document", source=filename
            )

    # ── Return SSE stream ─────────────────────────────────────────────────────
    return StreamingResponse(
        stream_agent_response(user_id, conversation_id, message, db, body.use_tools),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",        # Nginx: disable buffering
            "X-Conversation-Id": conversation_id,
        },
    )


# ─── GET /chat/conversations ──────────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user."""
    from sqlalchemy import select
    from app.memory.long_term import Conversation

    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    conversations = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]


# ─── DELETE /chat/conversations/{id} ─────────────────────────────────────────

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and its messages."""
    from sqlalchemy import select, delete as sql_delete
    from app.memory.long_term import Conversation, Message

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.execute(
        sql_delete(Message).where(
            Message.conversation_id == uuid.UUID(conversation_id)
        )
    )
    await db.delete(conv)
    await db.commit()

    # Clear Redis session too
    await memory_manager.clear_session(str(current_user.id), conversation_id)

    return {"message": "Conversation deleted", "id": conversation_id}
