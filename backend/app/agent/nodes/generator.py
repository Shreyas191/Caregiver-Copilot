"""generator node (CC-030, CC-034).

Runs the GLM tool-calling loop with the full tool set.
On regeneration, injects verifier issues as constraints.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.agent.tools import get_context_tools, get_write_tools, set_session
from app.agent.tools.clinical_tools import get_clinical_tools
from app.agent.tools.comms_tools import get_comms_tools
from app.agent.tools.urgency import get_urgency_tools
from app.agent.tools.types import Tool
from app.core.config import get_settings
from app.providers.factory import get_generator_provider
from app.providers.types import ChatResponse, Message, ToolDefinition, ToolFunction

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10

# Registry mapping stream_id → asyncio.Queue so the route can consume tokens
# as the generator produces them.  Entries are added/removed by chat.py.
_stream_queues: dict[str, asyncio.Queue] = {}


def register_stream(stream_id: str, queue: asyncio.Queue) -> None:
    _stream_queues[stream_id] = queue


def unregister_stream(stream_id: str) -> None:
    _stream_queues.pop(stream_id, None)
_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "v0_system.md"


def _tools_to_definitions(tools: list[Tool]) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            function=ToolFunction(
                name=t.name,
                description=t.description,
                parameters=t.input_schema,
            )
        )
        for t in tools
    ]


def _build_tool_map(tools: list[Tool]) -> dict[str, Tool]:
    return {t.name: t for t in tools}


async def _execute_tool(tool: Tool, arguments: dict) -> str:
    if "care_recipient_id" in arguments and isinstance(arguments["care_recipient_id"], str):
        arguments["care_recipient_id"] = uuid.UUID(arguments["care_recipient_id"])
    if "episode_id" in arguments and isinstance(arguments["episode_id"], str):
        arguments["episode_id"] = uuid.UUID(arguments["episode_id"])

    try:
        result = await tool.function(**arguments)
        if hasattr(result, "model_dump"):
            return json.dumps(result.model_dump(), default=str)
        if isinstance(result, list) and result and hasattr(result[0], "model_dump"):
            return json.dumps([r.model_dump() for r in result], default=str)
        if isinstance(result, list):
            return json.dumps(result, default=str)
        return json.dumps(result, default=str)
    except Exception as e:
        logger.error("Tool %s failed: %s", tool.name, e)
        return json.dumps({"error": str(e)})


def _build_system_prompt(state: AgentState) -> str:
    base = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    care_id = state["care_recipient_id"]
    context = state.get("retrieved_context", {})

    profile = context.get("profile", {})
    meds = context.get("medications", [])
    vitals = context.get("vitals", [])

    med_names = ", ".join(m.get("display_name", "") for m in meds) or "none on file"
    recent_vitals = "; ".join(
        f"{v.get('type')}: {v.get('value_systolic', '')}/{v.get('value_diastolic', '')} {v.get('unit', '')}"
        if v.get("value_systolic")
        else f"{v.get('type')}: {v.get('value_numeric', '')} {v.get('unit', '')}"
        for v in vitals[:3]
    ) or "none"

    context_block = (
        f"\n\n## Current Session Context\n"
        f"Care recipient ID: `{care_id}`\n"
        f"Patient: {profile.get('display_name', 'Unknown')}, "
        f"DOB: {profile.get('date_of_birth', 'unknown')}\n"
        f"Active medications: {med_names}\n"
        f"Recent vitals: {recent_vitals}\n"
        f"Use the care recipient ID above for ALL tool calls.\n"
    )

    # CC-034: inject verifier constraints on regeneration
    verifier_result = state.get("verifier_result")
    regen_count = state.get("regeneration_count", 0)
    if verifier_result and not verifier_result.get("passed") and regen_count > 0:
        issues = verifier_result.get("issues", [])
        if issues:
            issue_list = "\n".join(f"- {i.get('description', i)}" for i in issues)
            context_block += (
                f"\n## Verifier Feedback (Regeneration {regen_count})\n"
                f"Your previous response had the following issues. "
                f"Correct them in this response:\n{issue_list}\n"
            )

    return base + context_block


async def generator_node(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    """Run the tool-calling generator loop and return updated state fields."""
    settings = get_settings()
    set_session(db)

    all_tools = (
        get_context_tools()
        + get_write_tools()
        + get_clinical_tools()
        + get_urgency_tools()
        + get_comms_tools()
    )
    tool_defs = _tools_to_definitions(all_tools)
    tool_map = _build_tool_map(all_tools)

    system_prompt = _build_system_prompt(state)
    raw_messages = state.get("messages", [])

    # Build full conversation history so the model has multi-turn context.
    # System prompt goes first; then user/assistant turns from state.
    messages: list[Message] = [Message(role="system", content=system_prompt)]
    for m in raw_messages:
        role = m.get("role", "user")
        if role in ("user", "assistant"):
            messages.append(Message(role=role, content=m.get("content") or ""))

    all_tool_calls_log: list[dict[str, Any]] = list(state.get("tools_called", []))
    seen_calls: set[str] = set()  # dedup key: "tool_name:args_json"
    provider = get_generator_provider()
    model = settings.generator_model_name
    queue: asyncio.Queue | None = _stream_queues.get(state.get("stream_id", "") or "")

    try:
        for iteration in range(MAX_TOOL_ITERATIONS):
            response: ChatResponse = await provider.chat_with_tools(
                messages=messages,
                model=model,
                tools=tool_defs,
            )

            if not response.tool_calls:
                final_text = response.content or "I'm unable to generate a response."
                if queue is not None:
                    # Push already-fetched content word-by-word into the queue so
                    # the SSE route streams to the frontend while the verifier runs.
                    # No extra LLM call — reuses the response we already paid for.
                    words = final_text.split(" ")
                    for i, word in enumerate(words):
                        await queue.put(word if i == 0 else " " + word)
                return {
                    "final_response": final_text,
                    "tools_called": all_tool_calls_log,
                }

            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            for tc in response.tool_calls:
                tool_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                arguments_log = json.loads(json.dumps(arguments, default=str))
                dedup_key = f"{tool_name}:{json.dumps(arguments_log, sort_keys=True)}"

                if dedup_key in seen_calls:
                    # Return cached result to break the loop
                    result_str = json.dumps({"note": "Already called with these arguments. Use the previous result to compose your response."})
                else:
                    seen_calls.add(dedup_key)
                    tool = tool_map.get(tool_name)
                    if tool is None:
                        result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                    else:
                        result_str = await _execute_tool(tool, dict(arguments))

                all_tool_calls_log.append({
                    "iteration": iteration + 1,
                    "tool_call_id": tc.id,
                    "tool_name": tool_name,
                    "arguments": arguments_log,
                    "result": result_str[:500],
                })

                messages.append(
                    Message(role="tool", content=result_str, tool_call_id=tc.id)
                )

        return {
            "final_response": (
                "I apologize, but I'm having difficulty completing this request. "
                "Please contact the care recipient's healthcare provider directly if urgent."
            ),
            "tools_called": all_tool_calls_log,
        }

    finally:
        await provider.aclose()
