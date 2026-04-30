"""Write tools that persist observations (vitals, episodes) to the database.

Uses the same ContextVar-based session injection as context_tools.
Callers must call `set_session(session)` before invoking any tool function.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.context_tools import _get_session
from app.agent.tools.types import Tool
from app.models.enums import EpisodeStatus, UrgencyLevel, VitalSource, VitalType
from app.models.episode import Episode
from app.models.vital import Vital


# ------------------------------------------------------------------
# Output schemas
# ------------------------------------------------------------------


class VitalLogged(BaseModel):
    id: uuid.UUID
    summary: str


class EpisodeLogged(BaseModel):
    id: uuid.UUID
    summary: str


# ------------------------------------------------------------------
# Tool functions
# ------------------------------------------------------------------


async def log_vital(
    care_recipient_id: uuid.UUID,
    vital_type: str,
    unit: str,
    recorded_at: str | None = None,
    value_numeric: float | None = None,
    value_systolic: int | None = None,
    value_diastolic: int | None = None,
    value_text: str | None = None,
    notes: str | None = None,
) -> VitalLogged:
    """Log a vital-sign reading for a care recipient.

    For blood_pressure type, both value_systolic and value_diastolic are
    required; value_numeric must NOT be the only value supplied.
    """
    # Validate vital_type is a known enum value
    try:
        vt = VitalType(vital_type)
    except ValueError:
        valid = [e.value for e in VitalType]
        raise ValueError(
            f"Invalid vital_type '{vital_type}'. Must be one of: {valid}"
        )

    # BP-specific validation
    if vt == VitalType.blood_pressure:
        if value_systolic is None or value_diastolic is None:
            raise ValueError(
                "Blood pressure readings require both value_systolic and value_diastolic."
            )
    else:
        # Non-BP vitals should have at least one value
        if value_numeric is None and value_text is None:
            raise ValueError(
                f"Vital type '{vital_type}' requires value_numeric or value_text."
            )

    # Parse recorded_at or default to now
    if recorded_at is not None:
        if isinstance(recorded_at, str):
            ts = datetime.fromisoformat(recorded_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = recorded_at
    else:
        ts = datetime.now(tz=timezone.utc)

    session = _get_session()

    vital = Vital(
        care_recipient_id=care_recipient_id,
        type=vt,
        value_numeric=value_numeric,
        value_systolic=value_systolic,
        value_diastolic=value_diastolic,
        value_text=value_text,
        unit=unit,
        recorded_at=ts,
        source=VitalSource.manual,
        notes=notes,
    )
    session.add(vital)
    await session.flush()  # populates vital.id

    summary_parts = [f"Logged {vt.value}"]
    if vt == VitalType.blood_pressure:
        summary_parts.append(f"{value_systolic}/{value_diastolic} {unit}")
    elif value_numeric is not None:
        summary_parts.append(f"{value_numeric} {unit}")
    else:
        summary_parts.append(f"{value_text} {unit}")

    return VitalLogged(id=vital.id, summary=" — ".join(summary_parts))


async def log_episode(
    care_recipient_id: uuid.UUID,
    started_at: str | None,
    caregiver_description: str,
    urgency_level: str,
    symptoms: list[dict[str, Any]] | None = None,
    agent_assessment: str | None = None,
    recommended_actions: list[dict[str, Any]] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> EpisodeLogged:
    """Log a health episode for a care recipient.

    urgency_level must be one of: routine, same_day, urgent, emergency.
    """
    # Validate urgency_level
    try:
        ul = UrgencyLevel(urgency_level)
    except ValueError:
        valid = [e.value for e in UrgencyLevel]
        raise ValueError(
            f"Invalid urgency_level '{urgency_level}'. Must be one of: {valid}"
        )

    # Parse started_at or default to now
    if started_at is not None:
        if isinstance(started_at, str):
            ts = datetime.fromisoformat(started_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = started_at
    else:
        ts = datetime.now(tz=timezone.utc)

    session = _get_session()

    episode = Episode(
        care_recipient_id=care_recipient_id,
        started_at=ts,
        caregiver_description=caregiver_description,
        symptoms=symptoms or [],
        agent_assessment=agent_assessment,
        urgency_level=ul,
        recommended_actions=recommended_actions or [],
        citations=citations or [],
        status=EpisodeStatus.open,
    )
    session.add(episode)
    await session.flush()  # populates episode.id

    return EpisodeLogged(
        id=episode.id,
        summary=f"Logged episode ({ul.value}): {caregiver_description[:80]}",
    )


# ------------------------------------------------------------------
# Tool definitions (OpenAI-compatible schema)
# ------------------------------------------------------------------

LOG_VITAL = Tool(
    name="log_vital",
    description=(
        "Record a vital-sign reading (blood pressure, heart rate, glucose, etc.) "
        "for a care recipient. For blood_pressure, both value_systolic and "
        "value_diastolic are required."
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
                "enum": [e.value for e in VitalType],
                "description": "Type of vital sign being recorded",
            },
            "value_numeric": {
                "type": "number",
                "description": "Numeric value (use for non-BP vitals: HR, glucose, etc.)",
            },
            "value_systolic": {
                "type": "integer",
                "description": "Systolic blood pressure (required for blood_pressure type)",
            },
            "value_diastolic": {
                "type": "integer",
                "description": "Diastolic blood pressure (required for blood_pressure type)",
            },
            "value_text": {
                "type": "string",
                "description": "Free-text value (e.g., pain description)",
            },
            "unit": {
                "type": "string",
                "description": "Unit of measurement (e.g., mmHg, bpm, mg/dL)",
            },
            "recorded_at": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 timestamp of when the vital was taken (defaults to now)",
            },
            "notes": {
                "type": "string",
                "description": "Optional notes about the reading",
            },
        },
        "required": ["care_recipient_id", "vital_type", "unit"],
    },
    function=log_vital,
)

LOG_EPISODE = Tool(
    name="log_episode",
    description=(
        "Create a health episode to track a concerning event or symptom report "
        "for a care recipient. Includes the caregiver's description, symptoms, "
        "the agent's assessment, and recommended next steps."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            },
            "started_at": {
                "type": "string",
                "format": "date-time",
                "description": "When the episode started (ISO 8601, defaults to now)",
            },
            "caregiver_description": {
                "type": "string",
                "description": "The caregiver's description of what happened",
            },
            "symptoms": {
                "type": "array",
                "items": {"type": "object"},
                "description": 'List of symptom objects, e.g. [{"name": "dyspnea", "severity": "moderate"}]',
            },
            "agent_assessment": {
                "type": "string",
                "description": "The agent's clinical assessment summary",
            },
            "urgency_level": {
                "type": "string",
                "enum": [e.value for e in UrgencyLevel],
                "description": "How urgently the caregiver should act",
            },
            "recommended_actions": {
                "type": "array",
                "items": {"type": "object"},
                "description": 'List of action objects, e.g. [{"action": "call PCP", "reason": "..."}]',
            },
            "citations": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Source citations for any clinical claims",
            },
        },
        "required": ["care_recipient_id", "caregiver_description", "urgency_level"],
    },
    function=log_episode,
)


def get_write_tools() -> list[Tool]:
    """Return all write tools."""
    return [LOG_VITAL, LOG_EPISODE]
