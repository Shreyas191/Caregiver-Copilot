"""Tests for CC-027/029: comms tools (draft message, calendar tools)."""

import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.agent.tools.comms_tools import (
    get_comms_tools,
    DRAFT_PROVIDER_MESSAGE,
    SCHEDULE_RECHECK,
    SET_FOLLOWUP_REMINDER,
    schedule_recheck,
    set_followup_reminder,
)


def test_get_comms_tools_returns_three():
    tools = get_comms_tools()
    assert len(tools) == 3


def test_comms_tool_names():
    names = {t.name for t in get_comms_tools()}
    assert "draft_provider_message" in names
    assert "schedule_recheck" in names
    assert "set_followup_reminder" in names


def test_draft_provider_message_schema():
    props = DRAFT_PROVIDER_MESSAGE.input_schema["properties"]
    assert "episode_id" in props
    assert "episode_id" in DRAFT_PROVIDER_MESSAGE.input_schema["required"]


def test_schedule_recheck_schema():
    props = SCHEDULE_RECHECK.input_schema["properties"]
    assert "care_recipient_id" in props
    assert "vital_type" in props
    assert "offset_hours" in props


def test_set_followup_reminder_schema():
    props = SET_FOLLOWUP_REMINDER.input_schema["properties"]
    assert "care_recipient_id" in props
    assert "message" in props
    assert "offset_hours" in props


@pytest.mark.asyncio
async def test_schedule_recheck_no_calendar_returns_graceful():
    """Returns calendar_not_connected status when Google Calendar is not set up."""
    from app.agent.tools.schemas import CareRecipientContext
    from app.models.enums import SexAtBirth, ConsentBasis
    from datetime import date

    fake_profile = CareRecipientContext(
        id=uuid.uuid4(),
        display_name="Test Patient",
        date_of_birth=date(1948, 1, 1),
        sex_at_birth=SexAtBirth.female,
        consent_basis=ConsentBasis.power_of_attorney,
    )

    with patch("app.agent.tools.comms_tools.get_care_recipient_profile",
               new=AsyncMock(return_value=fake_profile)):
        with patch("app.agent.tools.comms_tools._get_session") as mock_session:
            mock_session.return_value = AsyncMock()
            with patch(
                "app.integrations.google_calendar.create_calendar_event",
                side_effect=RuntimeError("Google Calendar not connected — no OAuth token found"),
            ):
                result = await schedule_recheck(
                    care_recipient_id=uuid.uuid4(),
                    vital_type="blood_pressure",
                    offset_hours=4,
                )

    assert result.status == "calendar_not_connected"
    assert "connect Google Calendar" in result.summary or "Would schedule" in result.summary


@pytest.mark.asyncio
async def test_set_followup_reminder_no_calendar_returns_graceful():
    """Returns calendar_not_connected status gracefully."""
    from app.agent.tools.schemas import CareRecipientContext
    from app.models.enums import SexAtBirth, ConsentBasis
    from datetime import date

    fake_profile = CareRecipientContext(
        id=uuid.uuid4(),
        display_name="Test Patient",
        date_of_birth=date(1948, 1, 1),
        sex_at_birth=SexAtBirth.female,
        consent_basis=ConsentBasis.power_of_attorney,
    )

    with patch("app.agent.tools.comms_tools.get_care_recipient_profile",
               new=AsyncMock(return_value=fake_profile)):
        with patch("app.agent.tools.comms_tools._get_session") as mock_session:
            mock_session.return_value = AsyncMock()
            with patch(
                "app.integrations.google_calendar.create_calendar_event",
                side_effect=RuntimeError("Google Calendar not connected — no OAuth token found"),
            ):
                result = await set_followup_reminder(
                    care_recipient_id=uuid.uuid4(),
                    message="Check blood pressure again",
                    offset_hours=6,
                )

    assert result.status == "calendar_not_connected"
