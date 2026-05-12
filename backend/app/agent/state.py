"""LangGraph AgentState definition (CC-030)."""

from __future__ import annotations

import uuid
from typing import Any, Optional
from typing_extensions import TypedDict

from app.models.enums import MessageIntent, UrgencyLevel, VerifierSeverity


class VerifierResult(TypedDict, total=False):
    passed: bool
    issues: list[dict[str, str]]
    severity: str  # VerifierSeverity value


class AgentState(TypedDict, total=False):
    # Session identifiers
    care_recipient_id: uuid.UUID
    thread_id: Optional[uuid.UUID]
    caregiver_clerk_id: str

    # Conversation messages (OpenAI-format dicts for LangGraph compatibility)
    messages: list[dict[str, Any]]

    # Routing
    intent: str  # MessageIntent value
    intent_confidence: float

    # Context preloaded by context_loader node
    retrieved_context: dict[str, Any]

    # Generator state
    tools_called: list[dict[str, Any]]
    final_response: Optional[str]

    # Verifier state
    verifier_result: Optional[VerifierResult]
    regeneration_count: int

    # Error / escalation flag
    escalated: bool
