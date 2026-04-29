import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class Medication(Base, IDMixin, TimestampMixin):
    __tablename__ = "medications"

    care_recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_recipients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    display_name: Mapped[str] = mapped_column(String, nullable=False)
    rxnorm_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    rxnorm_name: Mapped[str | None] = mapped_column(String, nullable=True)

    dose: Mapped[str | None] = mapped_column(String, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String, nullable=True)
    route: Mapped[str | None] = mapped_column(String, nullable=True, default="oral")

    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    stopped_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    stopped_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    prescribed_for: Mapped[str | None] = mapped_column(String, nullable=True)
    prescriber: Mapped[str | None] = mapped_column(String, nullable=True)
