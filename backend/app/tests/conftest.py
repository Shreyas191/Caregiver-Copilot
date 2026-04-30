"""Shared pytest fixtures.

The main app engine uses a connection pool that is bound to the event loop
created at import time. pytest-asyncio creates a new event loop per test,
which causes "another operation is in progress" errors when pool connections
are reused across loop boundaries.

The fix is a NullPool engine for tests: no pooling means each session creates
and closes a fresh connection, so there's no loop-boundary mismatch.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Import all models so SQLAlchemy metadata is complete before any engine is created
import app.models.care_recipient  # noqa: F401
import app.models.caregiver  # noqa: F401
import app.models.conversation  # noqa: F401
import app.models.document  # noqa: F401
import app.models.episode  # noqa: F401
import app.models.external_api_cache  # noqa: F401
import app.models.medication  # noqa: F401
import app.models.provider_message  # noqa: F401
import app.models.vital  # noqa: F401
from app.core.config import get_settings

settings = get_settings()

_test_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=False,
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)

make_test_session = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
