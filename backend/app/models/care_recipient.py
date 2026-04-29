import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import ConsentBasis, SexAtBirth


class CareRecipient(Base, IDMixin, TimestampMixin):
    __tablename__ = "care_recipients"

    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("caregivers.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    display_name: Mapped[str] = mapped_column(String, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)

    sex_at_birth: Mapped[SexAtBirth] = mapped_column(
        ENUM(SexAtBirth, name="sex_at_birth", create_type=False), nullable=False
    )

    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    allergies: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    baseline_notes: Mapped[str | None] = mapped_column(String, nullable=True)

    primary_provider_name: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_provider_email: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_provider_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)

    consent_basis: Mapped[ConsentBasis] = mapped_column(
        ENUM(ConsentBasis, name="consent_basis", create_type=False), nullable=False
    )
    consent_documented_at: Mapped[datetime] = mapped_column(nullable=False)
    consent_revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
