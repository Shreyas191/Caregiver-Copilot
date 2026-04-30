"""Integration tests for CC-016 context-reading tools.

These tests seed data into the real database, exercise each tool, and clean up
afterwards. They require DATABASE_URL to be set and the DB to be reachable.

Run:
    pytest app/tests/test_context_tools.py -v
"""

import uuid
from datetime import date, datetime, timezone

import pytest

from app.agent.tools.context_tools import (
    get_active_medications,
    get_care_recipient_profile,
    get_context_tools,
    get_recent_episodes,
    get_recent_vitals,
    set_session,
)
from app.agent.tools.schemas import (
    ActiveMedication,
    CareRecipientContext,
    EpisodeSummary,
    VitalReading,
)
from app.agent.tools.types import Tool
from app.tests.conftest import make_test_session
from app.models.care_recipient import CareRecipient
from app.models.caregiver import Caregiver
from app.models.episode import Episode
from app.models.enums import (
    ConsentBasis,
    EpisodeStatus,
    SexAtBirth,
    UrgencyLevel,
    VitalSource,
    VitalType,
)
from app.models.medication import Medication
from app.models.vital import Vital


# ------------------------------------------------------------------
# Fixtures: seed + teardown
# ------------------------------------------------------------------


@pytest.fixture
async def seeded_db():
    """Create a caregiver, care recipient, medications, vitals, and episodes.
    Yields the care_recipient_id. Cleans up in reverse insertion order.

    Uses the NullPool test engine so each session gets a fresh connection,
    avoiding the event-loop / connection-pool mismatch in asyncpg 0.31.
    SQLAlchemy ID defaults run at flush time, so we flush after each dependent
    group to make the generated IDs available for FK references.
    """
    now = datetime.now(tz=timezone.utc)

    caregiver = Caregiver(
        clerk_user_id=f"test_clerk_{uuid.uuid4().hex}",
        display_name="Test Caregiver",
        email="testcaregiver@example.com",
    )
    async with make_test_session() as session:
        session.add(caregiver)
        await session.flush()  # populates caregiver.id

        recipient = CareRecipient(
            caregiver_id=caregiver.id,
            display_name="Jane Doe",
            date_of_birth=date(1945, 3, 15),
            sex_at_birth=SexAtBirth.female,
            conditions=[{"name": "Hypertension", "icd10_code": "I10"}],
            allergies=[{"substance": "Penicillin", "severity": "severe"}],
            baseline_notes="Generally frail; falls risk.",
            consent_basis=ConsentBasis.healthcare_proxy,
        )
        session.add(recipient)
        await session.flush()  # populates recipient.id

        med_active = Medication(
            care_recipient_id=recipient.id,
            display_name="Lisinopril",
            dose="10mg",
            frequency="once daily",
            route="oral",
            started_at=date(2023, 1, 1),
        )
        # Stopped medication — should NOT appear in get_active_medications
        med_stopped = Medication(
            care_recipient_id=recipient.id,
            display_name="Metformin",
            dose="500mg",
            frequency="twice daily",
            route="oral",
            started_at=date(2020, 6, 1),
            stopped_at=date(2022, 12, 31),
            stopped_reason="Discontinued by MD",
        )
        vital_bp = Vital(
            care_recipient_id=recipient.id,
            type=VitalType.blood_pressure,
            value_systolic=145,
            value_diastolic=92,
            unit="mmHg",
            recorded_at=now,
            source=VitalSource.manual,
        )
        vital_hr = Vital(
            care_recipient_id=recipient.id,
            type=VitalType.heart_rate,
            value_numeric=78,
            unit="bpm",
            recorded_at=now,
            source=VitalSource.manual,
        )
        episode = Episode(
            care_recipient_id=recipient.id,
            started_at=now,
            caregiver_description="Shortness of breath after walking.",
            symptoms=[{"name": "dyspnea", "severity": "moderate"}],
            urgency_level=UrgencyLevel.same_day,
            status=EpisodeStatus.open,
        )
        session.add_all([med_active, med_stopped, vital_bp, vital_hr, episode])
        await session.commit()

    recipient_id = recipient.id
    caregiver_id = caregiver.id

    yield recipient_id

    # Cleanup in FK-safe order
    async with make_test_session() as session:
        from sqlalchemy import delete

        await session.execute(
            delete(Episode).where(Episode.care_recipient_id == recipient_id)
        )
        await session.execute(
            delete(Vital).where(Vital.care_recipient_id == recipient_id)
        )
        await session.execute(
            delete(Medication).where(Medication.care_recipient_id == recipient_id)
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


# ------------------------------------------------------------------
# get_care_recipient_profile
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_returns_care_recipient_context(tool_session):
    result = await get_care_recipient_profile(tool_session)
    assert isinstance(result, CareRecipientContext)
    assert result.display_name == "Jane Doe"
    assert result.sex_at_birth == SexAtBirth.female


@pytest.mark.asyncio
async def test_profile_has_conditions_and_allergies(tool_session):
    result = await get_care_recipient_profile(tool_session)
    assert len(result.conditions) == 1
    assert result.conditions[0].name == "Hypertension"
    assert result.conditions[0].icd10_code == "I10"
    assert len(result.allergies) == 1
    assert result.allergies[0].substance == "Penicillin"


@pytest.mark.asyncio
async def test_profile_not_found_raises(tool_session):
    with pytest.raises(ValueError, match="not found"):
        await get_care_recipient_profile(uuid.uuid4())


# ------------------------------------------------------------------
# get_active_medications
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_active_medications_excludes_stopped(tool_session):
    result = await get_active_medications(tool_session)
    names = [m.display_name for m in result]
    assert "Lisinopril" in names
    assert "Metformin" not in names


@pytest.mark.asyncio
async def test_active_medications_returns_list(tool_session):
    result = await get_active_medications(tool_session)
    assert isinstance(result, list)
    assert all(isinstance(m, ActiveMedication) for m in result)


@pytest.mark.asyncio
async def test_active_medications_empty_for_unknown(tool_session):
    result = await get_active_medications(uuid.uuid4())
    assert result == []


# ------------------------------------------------------------------
# get_recent_vitals
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recent_vitals_returns_list(tool_session):
    result = await get_recent_vitals(tool_session)
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(v, VitalReading) for v in result)


@pytest.mark.asyncio
async def test_recent_vitals_filter_by_type(tool_session):
    result = await get_recent_vitals(tool_session, vital_type="blood_pressure")
    assert len(result) == 1
    assert result[0].type == VitalType.blood_pressure
    assert result[0].value_systolic == 145
    assert result[0].value_diastolic == 92


@pytest.mark.asyncio
async def test_recent_vitals_limit(tool_session):
    result = await get_recent_vitals(tool_session, limit=1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_recent_vitals_empty_for_unknown(tool_session):
    result = await get_recent_vitals(uuid.uuid4())
    assert result == []


# ------------------------------------------------------------------
# get_recent_episodes
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recent_episodes_returns_list(tool_session):
    result = await get_recent_episodes(tool_session)
    assert isinstance(result, list)
    assert len(result) == 1
    assert all(isinstance(e, EpisodeSummary) for e in result)


@pytest.mark.asyncio
async def test_recent_episodes_fields(tool_session):
    result = await get_recent_episodes(tool_session)
    ep = result[0]
    assert ep.caregiver_description == "Shortness of breath after walking."
    assert ep.urgency_level == UrgencyLevel.same_day
    assert ep.status == EpisodeStatus.open
    assert len(ep.symptoms) == 1


@pytest.mark.asyncio
async def test_recent_episodes_empty_for_unknown(tool_session):
    result = await get_recent_episodes(uuid.uuid4())
    assert result == []


# ------------------------------------------------------------------
# Tool registry
# ------------------------------------------------------------------


def test_get_context_tools_returns_four():
    tools = get_context_tools()
    assert len(tools) == 4
    assert all(isinstance(t, Tool) for t in tools)


def test_context_tool_names():
    names = {t.name for t in get_context_tools()}
    assert names == {
        "get_care_recipient_profile",
        "get_active_medications",
        "get_recent_vitals",
        "get_recent_episodes",
    }


def test_tool_input_schema_is_valid_json_schema():
    for tool in get_context_tools():
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert "care_recipient_id" in schema["required"]
