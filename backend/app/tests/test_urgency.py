"""Tests for CC-026: urgency assessment tool."""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agent.tools.urgency import assess_urgency, ASSESS_URGENCY, get_urgency_tools
from app.models.enums import UrgencyLevel
from app.providers.types import ChatResponse, UsageInfo


def _mock_provider(response_content: str):
    mock = AsyncMock()
    mock.chat = AsyncMock(return_value=ChatResponse(
        content=response_content,
        tool_calls=[],
        finish_reason="stop",
        usage=UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    ))
    mock.aclose = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_assess_urgency_emergency():
    payload = json.dumps({
        "level": "emergency",
        "reasoning": "Chest pain with radiation — possible cardiac event.",
        "red_flags": ["chest pain", "left arm radiation"],
    })
    with patch("app.agent.tools.urgency.get_generator_provider",
               return_value=_mock_provider(payload)):
        result = await assess_urgency(
            care_recipient_id=uuid.uuid4(),
            symptoms=["chest pain", "left arm pain"],
            vitals=[],
            medications=["aspirin"],
            context="Started 10 minutes ago",
        )
    assert result.level == UrgencyLevel.emergency
    assert len(result.red_flags) == 2


@pytest.mark.asyncio
async def test_assess_urgency_routine():
    payload = json.dumps({
        "level": "routine",
        "reasoning": "Mild stable knee pain, no red flags.",
        "red_flags": [],
    })
    with patch("app.agent.tools.urgency.get_generator_provider",
               return_value=_mock_provider(payload)):
        result = await assess_urgency(
            care_recipient_id=uuid.uuid4(),
            symptoms=["mild knee pain"],
            vitals=[],
            medications=[],
            context="Known osteoarthritis",
        )
    assert result.level == UrgencyLevel.routine
    assert result.red_flags == []


@pytest.mark.asyncio
async def test_assess_urgency_bad_json_fails_safe():
    """Falls back to 'urgent' when model returns unparseable JSON."""
    with patch("app.agent.tools.urgency.get_generator_provider",
               return_value=_mock_provider("I cannot determine this.")):
        result = await assess_urgency(
            care_recipient_id=uuid.uuid4(),
            symptoms=["something"],
            vitals=[],
            medications=[],
            context="",
        )
    assert result.level == UrgencyLevel.urgent


@pytest.mark.asyncio
async def test_assess_urgency_invalid_level_fails_safe():
    """Falls back to 'urgent' when model returns an unknown urgency level."""
    payload = json.dumps({"level": "critical", "reasoning": "...", "red_flags": []})
    with patch("app.agent.tools.urgency.get_generator_provider",
               return_value=_mock_provider(payload)):
        result = await assess_urgency(
            care_recipient_id=uuid.uuid4(),
            symptoms=[],
            vitals=[],
            medications=[],
            context="",
        )
    assert result.level == UrgencyLevel.urgent


@pytest.mark.asyncio
async def test_assess_urgency_strips_markdown_fences():
    """Handles response wrapped in ```json ... ```."""
    payload = '```json\n{"level": "same_day", "reasoning": "ok", "red_flags": []}\n```'
    with patch("app.agent.tools.urgency.get_generator_provider",
               return_value=_mock_provider(payload)):
        result = await assess_urgency(
            care_recipient_id=uuid.uuid4(),
            symptoms=["cough"],
            vitals=[],
            medications=[],
            context="",
        )
    assert result.level == UrgencyLevel.same_day


def test_urgency_tool_schema():
    assert ASSESS_URGENCY.name == "assess_urgency"
    required = ASSESS_URGENCY.input_schema["required"]
    for field in ["care_recipient_id", "symptoms", "vitals", "medications", "context"]:
        assert field in required


def test_get_urgency_tools():
    tools = get_urgency_tools()
    assert len(tools) == 1
    assert tools[0].name == "assess_urgency"
