import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import EpisodeStatus, UrgencyLevel


class Episode(Base, IDMixin, TimestampMixin):
    __tablename__ = "episodes"

    care_recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    caregiver_description: Mapped[str] = mapped_column(String, nullable=False)

    symptoms: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    agent_assessment: Mapped[str | None] = mapped_column(String, nullable=True)
    urgency_level: Mapped[UrgencyLevel] = mapped_column(
        ENUM(UrgencyLevel, name="urgency_level", create_type=False), nullable=False
    )

    recommended_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    status: Mapped[EpisodeStatus] = mapped_column(
        ENUM(EpisodeStatus, name="episode_status", create_type=False),
        nullable=False,
        default=EpisodeStatus.open,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String, nullable=True)
