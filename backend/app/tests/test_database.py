import pytest
from sqlalchemy import select, text

from app.core.database import async_session_maker
from app.models.caregiver import Caregiver


@pytest.mark.asyncio
async def test_database_connection():
    """Verify that we can connect to the database and query the caregivers table."""
    async with async_session_maker() as session:
        # A simple query to ensure models and connection work
        result = await session.execute(select(Caregiver).limit(1))
        # Result should be iterable/scalarable, though likely empty in a clean test DB
        rows = result.scalars().all()
        assert isinstance(rows, list)



