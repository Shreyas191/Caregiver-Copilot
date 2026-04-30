"""Read-only context tools that load care recipient data from the database.

The async session is injected via a ContextVar. Callers (agent loop, tests)
must call `set_session(session)` before invoking any tool function.

Usage:
    from app.agent.tools.context_tools import set_session, get_context_tools

    set_session(db_session)
    profile = await get_care_recipient_profile(care_recipient_id)
"""

import uuid
from contextvars import ContextVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.schemas import (
    ActiveMedication,
    AllergyItem,
    CareRecipientContext,
    ConditionItem,
    EpisodeSummary,
    VitalReading,
)
from app.agent.tools.types import Tool
from app.models.care_recipient import CareRecipient
from app.models.episode import Episode
from app.models.medication import Medication
from app.models.vital import Vital

_session_var: ContextVar[AsyncSession] = ContextVar("agent_db_session")


def set_session(session: AsyncSession) -> None:
    """Bind a database session to the current async context."""
    _session_var.set(session)


def _get_session() -> AsyncSession:
    try:
        return _session_var.get()
    except LookupError as exc:
        raise RuntimeError(
            "No database session bound. Call set_session() before using context tools."
        ) from exc


# ------------------------------------------------------------------
# Tool functions
# ------------------------------------------------------------------


async def get_care_recipient_profile(care_recipient_id: uuid.UUID) -> CareRecipientContext:
    """Return demographic and medical background for a care recipient."""
    session = _get_session()
    result = await session.execute(
        select(CareRecipient).where(CareRecipient.id == care_recipient_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"CareRecipient {care_recipient_id} not found")

    conditions = [ConditionItem(**c) for c in (row.conditions or [])]
    allergies = [AllergyItem(**a) for a in (row.allergies or [])]

    return CareRecipientContext(
        id=row.id,
        display_name=row.display_name,
        date_of_birth=row.date_of_birth,
        sex_at_birth=row.sex_at_birth,
        conditions=conditions,
        allergies=allergies,
        baseline_notes=row.baseline_notes,
        primary_provider_name=row.primary_provider_name,
        primary_provider_email=row.primary_provider_email,
        primary_provider_phone=row.primary_provider_phone,
        emergency_contact_name=row.emergency_contact_name,
        emergency_contact_phone=row.emergency_contact_phone,
        consent_basis=row.consent_basis,
    )


async def get_active_medications(care_recipient_id: uuid.UUID) -> list[ActiveMedication]:
    """Return all medications that have not been stopped."""
    session = _get_session()
    result = await session.execute(
        select(Medication)
        .where(
            Medication.care_recipient_id == care_recipient_id,
            Medication.stopped_at.is_(None),
        )
        .order_by(Medication.started_at.desc())
    )
    rows = result.scalars().all()
    return [
        ActiveMedication(
            id=m.id,
            display_name=m.display_name,
            rxnorm_code=m.rxnorm_code,
            rxnorm_name=m.rxnorm_name,
            dose=m.dose,
            frequency=m.frequency,
            route=m.route,
            started_at=m.started_at,
            prescribed_for=m.prescribed_for,
            prescriber=m.prescriber,
        )
        for m in rows
    ]


async def get_recent_vitals(
    care_recipient_id: uuid.UUID,
    vital_type: str | None = None,
    limit: int = 10,
) -> list[VitalReading]:
    """Return recent vital readings, optionally filtered by vital_type."""
    session = _get_session()
    stmt = (
        select(Vital)
        .where(Vital.care_recipient_id == care_recipient_id)
        .order_by(Vital.recorded_at.desc())
        .limit(limit)
    )
    if vital_type is not None:
        from app.models.enums import VitalType

        stmt = stmt.where(Vital.type == VitalType(vital_type))

    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        VitalReading(
            id=v.id,
            type=v.type,
            value_numeric=float(v.value_numeric) if v.value_numeric is not None else None,
            value_systolic=v.value_systolic,
            value_diastolic=v.value_diastolic,
            value_text=v.value_text,
            unit=v.unit,
            recorded_at=v.recorded_at,
            source=v.source,
            notes=v.notes,
        )
        for v in rows
    ]


async def get_recent_episodes(
    care_recipient_id: uuid.UUID,
    limit: int = 5,
) -> list[EpisodeSummary]:
    """Return recent health episodes, most recent first."""
    session = _get_session()
    result = await session.execute(
        select(Episode)
        .where(Episode.care_recipient_id == care_recipient_id)
        .order_by(Episode.started_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        EpisodeSummary(
            id=e.id,
            started_at=e.started_at,
            caregiver_description=e.caregiver_description,
            symptoms=e.symptoms or [],
            agent_assessment=e.agent_assessment,
            urgency_level=e.urgency_level,
            recommended_actions=e.recommended_actions or [],
            status=e.status,
            resolved_at=e.resolved_at,
            created_at=e.created_at,
        )
        for e in rows
    ]


# ------------------------------------------------------------------
# Tool definitions (OpenAI-compatible schema)
# ------------------------------------------------------------------

GET_CARE_RECIPIENT_PROFILE = Tool(
    name="get_care_recipient_profile",
    description=(
        "Retrieve the demographic and medical background of a care recipient, "
        "including conditions, allergies, baseline notes, and provider contacts."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            }
        },
        "required": ["care_recipient_id"],
    },
    function=get_care_recipient_profile,
)

GET_ACTIVE_MEDICATIONS = Tool(
    name="get_active_medications",
    description="Return all active (not stopped) medications for a care recipient.",
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            }
        },
        "required": ["care_recipient_id"],
    },
    function=get_active_medications,
)

GET_RECENT_VITALS = Tool(
    name="get_recent_vitals",
    description=(
        "Return recent vital-sign readings for a care recipient, newest first. "
        "Optionally filter by vital type (e.g. 'blood_pressure', 'heart_rate')."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            },
            "vital_type": {
                "type": "string",
                "enum": [
                    "blood_pressure",
                    "heart_rate",
                    "glucose",
                    "weight",
                    "temperature",
                    "oxygen_saturation",
                    "respiratory_rate",
                    "pain_score",
                ],
                "description": "Filter to a specific vital type (optional)",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 10,
                "description": "Maximum number of readings to return",
            },
        },
        "required": ["care_recipient_id"],
    },
    function=get_recent_vitals,
)

GET_RECENT_EPISODES = Tool(
    name="get_recent_episodes",
    description=(
        "Return recent health episodes for a care recipient, most recent first. "
        "Each episode includes the caregiver description, urgency level, and agent assessment."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "Maximum number of episodes to return",
            },
        },
        "required": ["care_recipient_id"],
    },
    function=get_recent_episodes,
)


def get_context_tools() -> list[Tool]:
    """Return all read-only context tools."""
    return [
        GET_CARE_RECIPIENT_PROFILE,
        GET_ACTIVE_MEDICATIONS,
        GET_RECENT_VITALS,
        GET_RECENT_EPISODES,
    ]
