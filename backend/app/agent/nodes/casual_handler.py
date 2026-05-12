"""casual_handler node (CC-032).

Fast path for non-clinical messages using Qwen3-8B with no tools.
"""

from __future__ import annotations

from typing import Any

from app.agent.state import AgentState
from app.core.config import get_settings
from app.providers.factory import get_router_provider
from app.providers.types import Message

_CASUAL_SYSTEM = (
    "You are a friendly and helpful caregiver assistant. "
    "Answer the caregiver's non-clinical question warmly and concisely. "
    "If the question turns clinical, let them know you can help with that too."
)


async def casual_handler_node(state: AgentState) -> dict[str, Any]:
    """Handle casual/non-clinical messages directly without tool calls."""
    settings = get_settings()
    raw_messages = state.get("messages", [])

    # Build full message list with history so the model has conversation context
    api_messages: list[Message] = [Message(role="system", content=_CASUAL_SYSTEM)]
    for m in raw_messages:
        role = m.get("role", "user")
        if role in ("user", "assistant"):
            api_messages.append(Message(role=role, content=m.get("content", "")))

    provider = get_router_provider()
    try:
        response = await provider.chat(
            messages=api_messages,
            model=settings.router_model_name,
        )
        return {
            "final_response": response.content or "How can I help you today?",
            "tools_called": [],
        }
    finally:
        await provider.aclose()
