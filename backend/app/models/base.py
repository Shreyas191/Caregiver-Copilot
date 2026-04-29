import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


class IDMixin:
    """Provides a primary key UUID column."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Provides created_at and updated_at timestamp columns."""
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), nullable=False
    )
    # updated_at is primarily updated via postgres triggers, but we set onupdate here
    # so the ORM models reflect the updated value if modified via SQLAlchemy
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), nullable=False
    )
