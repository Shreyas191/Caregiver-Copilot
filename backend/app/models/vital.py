import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin
from app.models.enums import VitalSource, VitalType


class Vital(Base, IDMixin):
    __tablename__ = "vitals"

    care_recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    type: Mapped[VitalType] = mapped_column(
        ENUM(VitalType, name="vital_type", create_type=False), nullable=False
    )

    value_numeric: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    value_systolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_diastolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String, nullable=True)
    unit: Mapped[str] = mapped_column(String, nullable=False)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[VitalSource] = mapped_column(
        ENUM(VitalSource, name="vital_source", create_type=False),
        nullable=False,
        default=VitalSource.manual,
    )
    
    # We will just map it to UUID for now since Document model is defined later,
    # or we can use a string reference.
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    episode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True
    )

    # Vitals do not have updated_at according to the schema
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
