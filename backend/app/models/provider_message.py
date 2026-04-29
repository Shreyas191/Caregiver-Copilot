import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import ProviderMessageStatus


class ProviderMessage(Base, IDMixin, TimestampMixin):
    __tablename__ = "provider_messages"

    episode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    recipient_name: Mapped[str] = mapped_column(String, nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String, nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String, nullable=True)

    subject: Mapped[str] = mapped_column(String, nullable=False)
    draft_content: Mapped[str] = mapped_column(String, nullable=False)

    status: Mapped[ProviderMessageStatus] = mapped_column(
        ENUM(ProviderMessageStatus, name="provider_message_status", create_type=False),
        nullable=False,
        default=ProviderMessageStatus.draft,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_via: Mapped[str | None] = mapped_column(String, nullable=True)
