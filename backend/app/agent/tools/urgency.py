"""Urgency assessment tool (CC-026).

Uses the generator model with a structured rubric to classify the urgency level
of a clinical situation. Fails safe toward higher urgency on ambiguous input.
"""

import json
import uuid
from pathlib import Path

from pydantic import BaseModel

from app.agent.tools.types import Tool
from app.models.enums import UrgencyLevel
from app.providers.factory import get_generator_provider
from app.providers.types import Message

_RUBRIC_PATH = Path(__file__).parent.parent / "prompts" / "urgency_rubric.md"


class UrgencyAssessment(BaseModel):
    level: UrgencyLevel
    reasoning: str
    red_flags: list[str]


async def assess_urgency(
    care_recipient_id: uuid.UUID,
    symptoms: list[str],
    vitals: list[dict],
    medications: list[str],
    context: str,
) -> UrgencyAssessment:
    """Assess the urgency level of a clinical picture.

    Fails safe toward 'urgent' when the model response is ambiguous or unparseable.
    """
    from app.core.config import get_settings

    settings = get_settings()
    rubric = _RUBRIC_PATH.read_text(encoding="utf-8")

    patient_summary = (
        f"Symptoms: {', '.join(symptoms) if symptoms else 'none reported'}\n"
        f"Recent vitals: {json.dumps(vitals, default=str) if vitals else 'not provided'}\n"
        f"Current medications: {', '.join(medications) if medications else 'none known'}\n"
        f"Additional context: {context or 'none'}"
    )

    user_message = (
        f"{rubric}\n\n"
        f"## Patient Situation\n\n{patient_summary}\n\n"
        f"Assess the urgency level and respond with JSON only."
    )

    provider = get_generator_provider()
    try:
        response = await provider.chat(
            messages=[Message(role="user", content=user_message)],
            model=settings.generator_model_name,
        )

        raw = (response.content or "").strip()
        # Strip markdown code fences if present
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                stripped = part.strip().lstrip("json").strip()
                if stripped.startswith("{"):
                    raw = stripped
                    break

        parsed = json.loads(raw)
        level_str = parsed.get("level", "urgent")
        try:
            level = UrgencyLevel(level_str)
        except ValueError:
            level = UrgencyLevel.urgent  # fail safe

        return UrgencyAssessment(
            level=level,
            reasoning=parsed.get("reasoning", "Unable to determine reasoning."),
            red_flags=parsed.get("red_flags", []),
        )

    except (json.JSONDecodeError, KeyError, AttributeError):
        # If parsing fails, fail safe toward urgent
        return UrgencyAssessment(
            level=UrgencyLevel.urgent,
            reasoning=(
                "Unable to complete automated urgency assessment. "
                "Out of caution, treating this as urgent. Please contact the care provider."
            ),
            red_flags=[],
        )
    finally:
        await provider.aclose()


ASSESS_URGENCY = Tool(
    name="assess_urgency",
    description=(
        "Assess the urgency level of a clinical situation using a structured medical rubric. "
        "Returns one of: routine, same_day, urgent, or emergency — along with reasoning "
        "and any identified red flags. Errs toward higher urgency when uncertain."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            },
            "symptoms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of reported symptoms (e.g. ['confusion', 'elevated BP'])",
            },
            "vitals": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of recent vital readings as dicts",
            },
            "medications": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of active medication names",
            },
            "context": {
                "type": "string",
                "description": "Additional context from the caregiver's message",
            },
        },
        "required": ["care_recipient_id", "symptoms", "vitals", "medications", "context"],
    },
    function=assess_urgency,
)


def get_urgency_tools() -> list[Tool]:
    return [ASSESS_URGENCY]
