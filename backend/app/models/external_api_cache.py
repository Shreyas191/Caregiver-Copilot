from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExternalApiCache(Base):
    __tablename__ = "external_api_cache"

    cache_key: Mapped[str] = mapped_column(String, primary_key=True)
    service: Mapped[str] = mapped_column(String, nullable=False)
    response_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
