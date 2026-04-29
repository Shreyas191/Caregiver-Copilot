import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import MessageIntent, MessageRole, VerifierSeverity


class ConversationThread(Base, IDMixin, TimestampMixin):
    __tablename__ = "conversation_threads"

    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("caregivers.id", ondelete="CASCADE"), nullable=False
    )
    care_recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)


class ConversationMessage(Base, IDMixin):
    __tablename__ = "conversation_messages"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("caregivers.id"), nullable=False
    )
    care_recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id"), nullable=False, index=True
    )

    role: Mapped[MessageRole] = mapped_column(
        ENUM(MessageRole, name="message_role", create_type=False), nullable=False
    )
    content: Mapped[str] = mapped_column(String, nullable=False)

    intent: Mapped[MessageIntent | None] = mapped_column(
        ENUM(MessageIntent, name="message_intent", create_type=False), nullable=True
    )
    intent_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    retrieved_context: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    verifier_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    verifier_severity: Mapped[VerifierSeverity | None] = mapped_column(
        ENUM(VerifierSeverity, name="verifier_severity", create_type=False), nullable=True
    )
    verifier_issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    regeneration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    episode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True
    )

    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
