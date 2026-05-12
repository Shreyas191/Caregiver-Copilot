"""escalation node (CC-034).

Called when the verifier fails after max regeneration attempts.
Returns a conservative safe response and flags the message for admin review.
"""

from __future__ import annotations

from typing import Any

from app.agent.state import AgentState


_ESCALATION_TEMPLATE = (
    "I want to make sure I give you accurate information here. "
    "Based on what you've described, I recommend contacting {provider} today. "
    "If this is urgent, please call 911 or go to the nearest emergency room."
)


async def escalation_node(state: AgentState) -> dict[str, Any]:
    """Replace the response with a safe conservative message."""
    context = state.get("retrieved_context", {})
    profile = context.get("profile", {})
    provider_name = profile.get("primary_provider_name") or "your care recipient's provider"

    safe_response = _ESCALATION_TEMPLATE.format(provider=provider_name)

    return {
        "final_response": safe_response,
        "escalated": True,
    }
