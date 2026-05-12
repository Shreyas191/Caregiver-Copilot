"""router node (CC-031).

Classifies the user's intent using Qwen3-8B with a few-shot prompt.
Low-confidence cases default to symptom_report (fail-safe to clinical path).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.agent.state import AgentState
from app.core.config import get_settings
from app.models.enums import MessageIntent
from app.providers.factory import get_router_provider
from app.providers.types import Message

logger = logging.getLogger(__name__)

_ROUTER_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "router.md"
_CONFIDENCE_THRESHOLD = 0.7


async def router_node(state: AgentState) -> dict[str, Any]:
    """Classify the user message intent using the router model."""
    settings = get_settings()
    messages = state.get("messages", [])
    user_content = messages[-1]["content"] if messages else ""

    router_prompt = _ROUTER_PROMPT_PATH.read_text(encoding="utf-8")

    # Include the immediately prior assistant turn as context so short follow-ups
    # like "yes" or "tell me more" are classified correctly.
    context_block = ""
    if len(messages) >= 2:
        prior = messages[-2]
        if prior.get("role") == "assistant" and prior.get("content"):
            snippet = prior["content"][:300].replace("\n", " ")
            context_block = f"\n\n## Prior assistant message (context)\n{snippet}\n"

    prompt = (
        f"{router_prompt}"
        f"{context_block}\n\n"
        f"## Message to classify\n\n{user_content}\n\n"
        f"Respond with JSON only: "
        f'{{ "intent": "<intent>", "confidence": <0.0-1.0> }}'
    )

    provider = get_router_provider()
    try:
        response = await provider.chat(
            messages=[Message(role="user", content=prompt)],
            model=settings.router_model_name,
        )

        raw = (response.content or "{}").strip()
        if "```" in raw:
            for part in raw.split("```"):
                stripped = part.strip().lstrip("json").strip()
                if stripped.startswith("{"):
                    raw = stripped
                    break

        parsed = json.loads(raw)
        intent_str = parsed.get("intent", "symptom_report")
        confidence = float(parsed.get("confidence", 0.5))

        # Validate intent is a known value
        valid_intents = {e.value for e in MessageIntent}
        if intent_str not in valid_intents:
            intent_str = MessageIntent.symptom_report.value
            confidence = 0.5

        # Fail safe: low-confidence routes to clinical path
        if confidence < _CONFIDENCE_THRESHOLD and intent_str != MessageIntent.symptom_report.value:
            logger.info(
                "Router confidence %.2f < %.2f for intent '%s'; defaulting to symptom_report",
                confidence,
                _CONFIDENCE_THRESHOLD,
                intent_str,
            )
            intent_str = MessageIntent.symptom_report.value

    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logger.warning("Router failed to parse response: %s", e)
        intent_str = MessageIntent.symptom_report.value
        confidence = 0.5
    finally:
        await provider.aclose()

    return {
        "intent": intent_str,
        "intent_confidence": confidence,
    }
