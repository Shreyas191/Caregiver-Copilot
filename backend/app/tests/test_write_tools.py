"""Integration tests for CC-017 write tools (log_vital, log_episode).

These tests seed data into the real database, exercise each write tool,
assert on the result and DB state, and clean up afterwards.

Run:
    pytest app/tests/test_write_tools.py -v
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import delete, select

from app.agent.tools.context_tools import set_session
from app.agent.tools.write_tools import (
    EpisodeLogged,
    VitalLogged,
    get_write_tools,
    log_episode,
    log_vital,
)
from app.agent.tools.types import Tool
from app.models.care_recipient import CareRecipient
from app.models.caregiver import Caregiver
from app.models.enums import (
    ConsentBasis,
    EpisodeStatus,
    SexAtBirth,
    UrgencyLevel,
    VitalType,
)
from app.models.episode import Episode
from app.models.vital import Vital
from app.tests.conftest import make_test_session


# ------------------------------------------------------------------
# Fixtures: seed + teardown
# ------------------------------------------------------------------


@pytest.fixture
async def seeded_db():
    """Create a caregiver and care recipient. Yields the care_recipient_id."""
    caregiver = Caregiver(
        clerk_user_id=f"test_clerk_{uuid.uuid4().hex}",
        display_name="Test Caregiver",
        email="testcg_write@example.com",
    )
    async with make_test_session() as session:
        session.add(caregiver)
        await session.flush()

        recipient = CareRecipient(
            caregiver_id=caregiver.id,
            display_name="John Doe",
            date_of_birth=date(1950, 7, 20),
            sex_at_birth=SexAtBirth.male,
            conditions=[{"name": "Type 2 Diabetes"}],
            allergies=[],
            consent_basis=ConsentBasis.self,
        )
        session.add(recipient)
        await session.commit()

    recipient_id = recipient.id
    caregiver_id = caregiver.id

    yield recipient_id

    # Cleanup
    async with make_test_session() as session:
        await session.execute(
            delete(Episode).where(Episode.care_recipient_id == recipient_id)
        )
        await session.execute(
            delete(Vital).where(Vital.care_recipient_id == recipient_id)
        )
        await session.execute(
            delete(CareRecipient).where(CareRecipient.id == recipient_id)
        )
        await session.execute(
            delete(Caregiver).where(Caregiver.id == caregiver_id)
        )
        await session.commit()


@pytest.fixture
async def tool_session(seeded_db):
    """Bind a session to the ContextVar and yield the care_recipient_id."""
    async with make_test_session() as session:
        set_session(session)
        yield seeded_db
        # Commit any writes made by tools so cleanup can see them
        await session.commit()


# ------------------------------------------------------------------
# log_vital — success cases
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_vital_bp_success(tool_session):
    """Blood pressure with systolic + diastolic should insert correctly."""
    result = await log_vital(
        care_recipient_id=tool_session,
        vital_type="blood_pressure",
        value_systolic=145,
        value_diastolic=92,
        unit="mmHg",
    )
    assert isinstance(result, VitalLogged)
    assert result.id is not None
    assert "blood_pressure" in result.summary
    assert "145/92" in result.summary


@pytest.mark.asyncio
async def test_log_vital_heart_rate_success(tool_session):
    """Heart rate with value_numeric should insert correctly."""
    result = await log_vital(
        care_recipient_id=tool_session,
        vital_type="heart_rate",
        value_numeric=78,
        unit="bpm",
    )
    assert isinstance(result, VitalLogged)
    assert result.id is not None
    assert "heart_rate" in result.summary


@pytest.mark.asyncio
async def test_log_vital_persisted_in_db(seeded_db):
    """Vital row should be visible in the database after logging."""
    async with make_test_session() as session:
        set_session(session)
        result = await log_vital(
            care_recipient_id=seeded_db,
            vital_type="glucose",
            value_numeric=120,
            unit="mg/dL",
            notes="Fasting reading",
        )
        await session.commit()

    async with make_test_session() as session:
        row = await session.execute(
            select(Vital).where(Vital.id == result.id)
        )
        vital = row.scalar_one()
        assert vital is not None
        assert vital.type == VitalType.glucose
        assert float(vital.value_numeric) == 120
        assert vital.notes == "Fasting reading"


@pytest.mark.asyncio
async def test_log_vital_with_custom_recorded_at(seeded_db):
    """Custom recorded_at should be preserved."""
    ts = "2024-06-15T10:30:00+00:00"
    async with make_test_session() as session:
        set_session(session)
        result = await log_vital(
            care_recipient_id=seeded_db,
            vital_type="temperature",
            value_numeric=98.6,
            unit="°F",
            recorded_at=ts,
        )
        await session.commit()
    assert isinstance(result, VitalLogged)

    async with make_test_session() as session:
        row = await session.execute(
            select(Vital).where(Vital.id == result.id)
        )
        vital = row.scalar_one()
        assert vital.recorded_at.year == 2024
        assert vital.recorded_at.month == 6


# ------------------------------------------------------------------
# log_vital — validation errors
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_vital_bp_missing_systolic_raises(tool_session):
    """BP with only value_numeric (no systolic/diastolic) should raise."""
    with pytest.raises(ValueError, match="value_systolic and value_diastolic"):
        await log_vital(
            care_recipient_id=tool_session,
            vital_type="blood_pressure",
            value_numeric=130,
            unit="mmHg",
        )


@pytest.mark.asyncio
async def test_log_vital_bp_missing_diastolic_raises(tool_session):
    """BP with only systolic (no diastolic) should raise."""
    with pytest.raises(ValueError, match="value_systolic and value_diastolic"):
        await log_vital(
            care_recipient_id=tool_session,
            vital_type="blood_pressure",
            value_systolic=145,
            unit="mmHg",
        )


@pytest.mark.asyncio
async def test_log_vital_invalid_type_raises(tool_session):
    """Invalid vital_type should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid vital_type"):
        await log_vital(
            care_recipient_id=tool_session,
            vital_type="blood_sugar_magic",
            value_numeric=100,
            unit="units",
        )


@pytest.mark.asyncio
async def test_log_vital_non_bp_no_value_raises(tool_session):
    """Non-BP vital with no numeric or text value should raise."""
    with pytest.raises(ValueError, match="requires value_numeric or value_text"):
        await log_vital(
            care_recipient_id=tool_session,
            vital_type="heart_rate",
            unit="bpm",
        )


# ------------------------------------------------------------------
# log_episode — success cases
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_episode_success(tool_session):
    """Basic episode should insert correctly."""
    result = await log_episode(
        care_recipient_id=tool_session,
        started_at=None,
        caregiver_description="Mom seemed confused this morning.",
        urgency_level="same_day",
        symptoms=[{"name": "confusion", "severity": "moderate"}],
        agent_assessment="Possible delirium; recommend same-day PCP visit.",
    )
    assert isinstance(result, EpisodeLogged)
    assert result.id is not None
    assert "same_day" in result.summary
    assert "confused" in result.summary


@pytest.mark.asyncio
async def test_log_episode_persisted_in_db(seeded_db):
    """Episode row should be visible in the database after logging."""
    async with make_test_session() as session:
        set_session(session)
        result = await log_episode(
            care_recipient_id=seeded_db,
            started_at="2024-06-15T08:00:00+00:00",
            caregiver_description="Shortness of breath after walking.",
            urgency_level="urgent",
            symptoms=[{"name": "dyspnea", "severity": "severe"}],
            recommended_actions=[{"action": "Call 911", "reason": "acute respiratory distress"}],
            citations=[{"source": "AHA guidelines", "url": "https://example.com"}],
        )
        await session.commit()

    async with make_test_session() as session:
        row = await session.execute(
            select(Episode).where(Episode.id == result.id)
        )
        episode = row.scalar_one()
        assert episode is not None
        assert episode.urgency_level == UrgencyLevel.urgent
        assert episode.status == EpisodeStatus.open
        assert episode.caregiver_description == "Shortness of breath after walking."
        assert len(episode.symptoms) == 1
        assert len(episode.recommended_actions) == 1
        assert len(episode.citations) == 1


@pytest.mark.asyncio
async def test_log_episode_minimal_fields(tool_session):
    """Episode with only required fields should work."""
    result = await log_episode(
        care_recipient_id=tool_session,
        started_at=None,
        caregiver_description="Fell asleep during dinner.",
        urgency_level="routine",
    )
    assert isinstance(result, EpisodeLogged)
    assert result.id is not None


# ------------------------------------------------------------------
# log_episode — validation errors
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_episode_invalid_urgency_raises(tool_session):
    """Invalid urgency_level should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid urgency_level"):
        await log_episode(
            care_recipient_id=tool_session,
            started_at=None,
            caregiver_description="Some event.",
            urgency_level="super_critical",
        )


@pytest.mark.asyncio
async def test_log_episode_another_invalid_urgency(tool_session):
    """Another invalid urgency value for coverage."""
    with pytest.raises(ValueError, match="Invalid urgency_level"):
        await log_episode(
            care_recipient_id=tool_session,
            started_at=None,
            caregiver_description="Something.",
            urgency_level="",
        )


# ------------------------------------------------------------------
# Tool registry
# ------------------------------------------------------------------


def test_get_write_tools_returns_two():
    tools = get_write_tools()
    assert len(tools) == 2
    assert all(isinstance(t, Tool) for t in tools)


def test_write_tool_names():
    names = {t.name for t in get_write_tools()}
    assert names == {"log_vital", "log_episode"}


def test_write_tool_schemas_are_valid():
    for tool in get_write_tools():
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert "care_recipient_id" in schema["required"]
