from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class Caregiver(Base, IDMixin, TimestampMixin):
    __tablename__ = "caregivers"

    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="America/New_York")
    google_oauth_token: Mapped[str | None] = mapped_column(String, nullable=True)
