from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.db import Base


# ─── DB Models ────────────────────────────────────────────────────────────────

class Conversation(Base):
    """Stores conversation metadata — messages are in Redis (short) or Message rows (archive)."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

   


class Message(Base):
    """Archived messages (written when conversation ends or exceeds Redis TTL)."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    role = Column(String(20), nullable=False)   # "user" | "assistant" | "tool"
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserFact(Base):
    """Long-term facts about a user that the agent should always remember."""
    __tablename__ = "user_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    category = Column(String(100), nullable=False)   # "preference" | "work" | "personal" | "context"
    key = Column(String(255), nullable=False)         # e.g. "preferred_language"
    value = Column(Text, nullable=False)              # e.g. "Hinglish"
    confidence = Column(String(20), default="high")  # "high" | "medium" | "low"
    source = Column(String(50), default="agent")     # "agent" | "user" | "inferred"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


# ─── Long Term Memory Service ─────────────────────────────────────────────────

class LongTermMemory:

    async def save_fact(self, db: AsyncSession, user_id: str, category: str,
                        key: str, value: str, source: str = "agent"):
        """Upsert a user fact. If key exists for user, update it."""
        result = await db.execute(
            select(UserFact).where(
                UserFact.user_id == uuid.UUID(user_id),
                UserFact.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value
            existing.source = source
            existing.updated_at = datetime.now(timezone.utc)
        else:
            fact = UserFact(
                user_id=uuid.UUID(user_id),
                category=category,
                key=key,
                value=value,
                source=source,
            )
            db.add(fact)
        await db.commit()

    async def get_facts(self, db: AsyncSession, user_id: str,
                        category: Optional[str] = None) -> List[UserFact]:
        """Retrieve all (or category-filtered) facts for a user."""
        query = select(UserFact).where(UserFact.user_id == uuid.UUID(user_id))
        if category:
            query = query.where(UserFact.category == category)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_facts_as_text(self, db: AsyncSession, user_id: str) -> str:
        """Format all user facts as a string for injection into system prompt."""
        facts = await self.get_facts(db, user_id)
        if not facts:
            return ""
        lines = ["Known facts about this user:"]
        for f in facts:
            lines.append(f"  [{f.category}] {f.key}: {f.value}")
        return "\n".join(lines)

    async def create_conversation(self, db: AsyncSession, user_id: str,
                                  title: Optional[str] = None) -> Conversation:
        conv = Conversation(user_id=uuid.UUID(user_id), title=title)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    async def archive_messages(self, db: AsyncSession, conversation_id: str,
                               messages: List[dict]):
        """Write Redis session messages into PostgreSQL for permanent storage."""
        for msg in messages:
            m = Message(
                conversation_id=uuid.UUID(conversation_id),
                role=msg["role"],
                content=msg["content"],
            )
            db.add(m)
        await db.commit()

    async def get_conversation_history(self, db: AsyncSession,
                                       conversation_id: str,
                                       limit: int = 50) -> List[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == uuid.UUID(conversation_id))
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))   # chronological order


long_term_memory = LongTermMemory()
