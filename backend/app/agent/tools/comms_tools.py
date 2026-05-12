"""Communication tools: draft provider messages, schedule rechecks and reminders.

CC-027: draft_provider_message
CC-029: schedule_recheck, set_followup_reminder
"""

import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from sqlalchemy import select

from app.agent.tools.context_tools import _get_session, get_active_medications, get_care_recipient_profile, get_recent_vitals
from app.agent.tools.types import Tool
from app.models.episode import Episode
from app.models.provider_message import ProviderMessage
from app.models.enums import ProviderMessageStatus


# ------------------------------------------------------------------
# CC-027: Draft provider message
# ------------------------------------------------------------------


class ProviderMessageDraft(BaseModel):
    id: uuid.UUID
    subject: str
    draft_content: str
    recipient_name: str


async def draft_provider_message(episode_id: uuid.UUID) -> ProviderMessageDraft:
    """Generate a clinically appropriate draft message to the PCP for an episode.

    Loads the episode, active medications, and recent vitals, then uses the
    generator model to write a professional medical communication.
    Saves the draft to the provider_messages table with status='draft'.
    """
    from app.providers.factory import get_generator_provider
    from app.providers.types import Message
    from app.core.config import get_settings

    db = _get_session()
    settings = get_settings()

    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if episode is None:
        raise ValueError(f"Episode {episode_id} not found")

    profile = await get_care_recipient_profile(episode.care_recipient_id)
    meds = await get_active_medications(episode.care_recipient_id)
    vitals = await get_recent_vitals(episode.care_recipient_id, limit=5)

    provider_name = profile.primary_provider_name or "Care Provider"
    patient_name = profile.display_name

    med_list = ", ".join(m.display_name for m in meds) if meds else "None on file"
    vitals_summary = (
        "; ".join(
            f"{v.type.value}: {v.value_systolic}/{v.value_diastolic} {v.unit}"
            if v.value_systolic
            else f"{v.type.value}: {v.value_numeric} {v.unit}"
            for v in vitals[:3]
        )
        if vitals
        else "Not available"
    )

    prompt = f"""You are helping a family caregiver draft a professional message to their
care recipient's primary care physician.

Patient: {patient_name}
Date of concern: {episode.started_at.strftime('%B %d, %Y')}
Urgency level: {episode.urgency_level.value}
Caregiver description: {episode.caregiver_description}
Agent assessment: {episode.agent_assessment or 'Not available'}
Current medications: {med_list}
Recent vitals: {vitals_summary}
Recommended actions: {', '.join(str(a) for a in (episode.recommended_actions or [])[:3]) or 'See details'}

Write a professional, concise medical communication to Dr. {provider_name} from the
caregiver's perspective. Include:
1. A clear subject line
2. Brief patient introduction and relationship
3. Description of the concern with relevant clinical details
4. Specific ask (appointment, callback, guidance)
5. Contact information placeholder

Format as JSON: {{"subject": "...", "body": "..."}}
"""

    provider = get_generator_provider()
    try:
        response = await provider.chat(
            messages=[Message(role="user", content=prompt)],
            model=settings.generator_model_name,
        )

        import json as _json

        raw = (response.content or "{}").strip()
        if "```" in raw:
            for part in raw.split("```"):
                stripped = part.strip().lstrip("json").strip()
                if stripped.startswith("{"):
                    raw = stripped
                    break

        try:
            parsed = _json.loads(raw)
            subject = parsed.get("subject", f"Regarding {patient_name} — {episode.urgency_level.value} concern")
            body = parsed.get("body", raw)
        except _json.JSONDecodeError:
            subject = f"Regarding {patient_name} — {episode.urgency_level.value} concern"
            body = raw

    finally:
        await provider.aclose()

    msg = ProviderMessage(
        episode_id=episode_id,
        recipient_name=provider_name,
        recipient_email=profile.primary_provider_email,
        recipient_phone=profile.primary_provider_phone,
        subject=subject,
        draft_content=body,
        status=ProviderMessageStatus.draft,
    )
    db.add(msg)
    await db.flush()

    return ProviderMessageDraft(
        id=msg.id,
        subject=subject,
        draft_content=body,
        recipient_name=provider_name,
    )


DRAFT_PROVIDER_MESSAGE = Tool(
    name="draft_provider_message",
    description=(
        "Generate a professional draft message to the care recipient's primary care "
        "physician based on a health episode. Saves the draft to the database and "
        "returns it for review. The caregiver can edit and send it later."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "episode_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the episode to draft a message about",
            }
        },
        "required": ["episode_id"],
    },
    function=draft_provider_message,
)


# ------------------------------------------------------------------
# CC-029: Calendar tools
# ------------------------------------------------------------------


class CalendarEventLogged(BaseModel):
    status: str
    summary: str
    scheduled_at: datetime | None = None


async def schedule_recheck(
    care_recipient_id: uuid.UUID,
    vital_type: str,
    offset_hours: int,
) -> CalendarEventLogged:
    """Schedule a reminder to recheck a vital sign in N hours via Google Calendar.

    Returns a 'calendar_not_connected' status gracefully if OAuth is not set up.
    """
    from app.integrations.google_calendar import create_calendar_event

    profile = await get_care_recipient_profile(care_recipient_id)
    db = _get_session()

    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    summary = f"Recheck {vital_type.replace('_', ' ')} for {profile.display_name}"
    description = (
        f"Reminder to check {vital_type.replace('_', ' ')} "
        f"for {profile.display_name} as requested by Caregiver Co-Pilot."
    )

    try:
        result = await create_calendar_event(
            db=db,
            care_recipient_id=care_recipient_id,
            summary=summary,
            description=description,
            start_time=scheduled_at,
            end_time=scheduled_at + timedelta(minutes=15),
        )
        return CalendarEventLogged(
            status="scheduled",
            summary=summary,
            scheduled_at=scheduled_at,
        )
    except Exception as e:
        error_str = str(e).lower()
        if "not connected" in error_str or "no token" in error_str or "oauth" in error_str:
            return CalendarEventLogged(
                status="calendar_not_connected",
                summary=f"Would schedule: {summary} in {offset_hours}h (connect Google Calendar in Settings)",
            )
        return CalendarEventLogged(
            status="error",
            summary=f"Could not schedule reminder: {e}",
        )


async def set_followup_reminder(
    care_recipient_id: uuid.UUID,
    message: str,
    offset_hours: int,
) -> CalendarEventLogged:
    """Set a follow-up reminder in Google Calendar at a specified offset from now.

    Returns 'calendar_not_connected' gracefully if OAuth is not configured.
    """
    from app.integrations.google_calendar import create_calendar_event

    profile = await get_care_recipient_profile(care_recipient_id)
    db = _get_session()

    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    summary = f"Follow-up: {message[:60]}"

    try:
        await create_calendar_event(
            db=db,
            care_recipient_id=care_recipient_id,
            summary=summary,
            description=f"Caregiver Co-Pilot reminder for {profile.display_name}: {message}",
            start_time=scheduled_at,
            end_time=scheduled_at + timedelta(minutes=15),
        )
        return CalendarEventLogged(
            status="scheduled",
            summary=summary,
            scheduled_at=scheduled_at,
        )
    except Exception as e:
        error_str = str(e).lower()
        if "not connected" in error_str or "no token" in error_str or "oauth" in error_str:
            return CalendarEventLogged(
                status="calendar_not_connected",
                summary=f"Would set reminder: {summary} in {offset_hours}h (connect Google Calendar in Settings)",
            )
        return CalendarEventLogged(
            status="error",
            summary=f"Could not set reminder: {e}",
        )


SCHEDULE_RECHECK = Tool(
    name="schedule_recheck",
    description=(
        "Schedule a Google Calendar reminder to recheck a vital sign in N hours. "
        "Returns 'calendar_not_connected' if the caregiver hasn't connected Google Calendar."
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
                "description": "Type of vital to recheck (e.g. 'blood_pressure', 'glucose')",
            },
            "offset_hours": {
                "type": "integer",
                "minimum": 1,
                "maximum": 168,
                "description": "Hours from now to schedule the reminder",
            },
        },
        "required": ["care_recipient_id", "vital_type", "offset_hours"],
    },
    function=schedule_recheck,
)

SET_FOLLOWUP_REMINDER = Tool(
    name="set_followup_reminder",
    description=(
        "Set a follow-up reminder in Google Calendar with a custom message at a specified "
        "time offset from now. Returns 'calendar_not_connected' if not yet connected."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            },
            "message": {
                "type": "string",
                "description": "Reminder message text",
            },
            "offset_hours": {
                "type": "integer",
                "minimum": 1,
                "maximum": 168,
                "description": "Hours from now to schedule the reminder",
            },
        },
        "required": ["care_recipient_id", "message", "offset_hours"],
    },
    function=set_followup_reminder,
)


def get_comms_tools() -> list[Tool]:
    return [DRAFT_PROVIDER_MESSAGE, SCHEDULE_RECHECK, SET_FOLLOWUP_REMINDER]
