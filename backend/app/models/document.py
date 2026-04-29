import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin
from app.models.enums import DocumentStatus, DocumentType


class Document(Base, IDMixin):
    __tablename__ = "documents"

    care_recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("caregivers.id"), nullable=False
    )

    type: Mapped[DocumentType] = mapped_column(
        ENUM(DocumentType, name="document_type", create_type=False), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        ENUM(DocumentStatus, name="document_status", create_type=False),
        nullable=False,
        default=DocumentStatus.uploaded,
    )

    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)

    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(String, nullable=True)

    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    processing_error: Mapped[str | None] = mapped_column(String, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
