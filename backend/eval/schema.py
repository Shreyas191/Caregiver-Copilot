"""CC-044: Pydantic schema for evaluation scenarios."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CareRecipientProfile(BaseModel):
    display_name: str
    age: int
    sex: str
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


class BehavioralCheck(BaseModel):
    check: str   # e.g. "response_contains", "tool_called", "no_hallucination"
    value: Any   # expected value or pattern


class EvalScenario(BaseModel):
    id: str
    category: str  # routine | urgency | drug_interaction | hallucination | document_qa
    care_recipient_profile: CareRecipientProfile
    message: str
    expected_intent: str | None = None
    expected_urgency: str | None = None          # routine | same_day | urgent | emergency
    expected_tool_calls: list[str] = Field(default_factory=list)
    behavioral_checks: list[BehavioralCheck] = Field(default_factory=list)
    notes: str | None = None
