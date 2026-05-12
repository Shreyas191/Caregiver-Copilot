"""verifier node (CC-033).

Independent review of generator output using Qwen3-30B (or configured verifier model).
Checks for hallucinations, urgency miscalibration, and safety boundary violations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.agent.state import AgentState, VerifierResult
from app.core.config import get_settings
from app.providers.factory import get_verifier_provider
from app.providers.types import Message

logger = logging.getLogger(__name__)

_VERIFIER_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "verifier.md"


def _summarise_tools(tools_called: list[dict]) -> str:
    if not tools_called:
        return "No tools were called."
    lines = []
    for tc in tools_called:
        name = tc.get("tool_name", "unknown")
        result = tc.get("result", "")[:200]
        lines.append(f"- {name}: {result}")
    return "\n".join(lines)


async def verifier_node(state: AgentState) -> dict[str, Any]:
    """Review the generator's output for accuracy and safety."""
    settings = get_settings()
    messages = state.get("messages", [])
    user_message = messages[-1]["content"] if messages else ""
    final_response = state.get("final_response", "")
    tools_called = state.get("tools_called", [])
    context = state.get("retrieved_context", {})

    rubric = _VERIFIER_PROMPT_PATH.read_text(encoding="utf-8")

    profile = context.get("profile", {})
    meds = context.get("medications", [])
    allergies = profile.get("allergies", [])

    tool_summary = _summarise_tools(tools_called)
    med_list = ", ".join(m.get("display_name", "") for m in meds) or "none"
    allergy_list = ", ".join(a.get("substance", "") for a in allergies) or "none"

    review_payload = (
        f"{rubric}\n\n"
        f"## Context from Tool Calls\n\n"
        f"Active medications: {med_list}\n"
        f"Known allergies: {allergy_list}\n"
        f"Patient: {profile.get('display_name', 'Unknown')}\n\n"
        f"## Tool Call Log\n\n{tool_summary}\n\n"
        f"## User Message\n\n{user_message}\n\n"
        f"## Assistant Response to Review\n\n{final_response}\n\n"
        f"Assess the response and return JSON only."
    )

    provider = get_verifier_provider()
    try:
        response = await provider.chat(
            messages=[Message(role="user", content=review_payload)],
            model=settings.verifier_model_name,
        )

        raw = (response.content or "{}").strip()
        if "```" in raw:
            for part in raw.split("```"):
                stripped = part.strip().lstrip("json").strip()
                if stripped.startswith("{"):
                    raw = stripped
                    break

        parsed = json.loads(raw)
        severity = parsed.get("severity", "none")
        passed = parsed.get("passed", severity in ("none", "low"))

        # Ensure passed is consistent with severity
        if severity in ("medium", "high"):
            passed = False
        elif severity in ("none", "low"):
            passed = True

        verifier_result: VerifierResult = {
            "passed": passed,
            "issues": parsed.get("issues", []),
            "severity": severity,
        }

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logger.warning("Verifier failed to parse response: %s", e)
        # On parse failure, pass through (don't block on verifier error)
        verifier_result = {
            "passed": True,
            "issues": [],
            "severity": "none",
        }
    finally:
        await provider.aclose()

    return {"verifier_result": verifier_result}
