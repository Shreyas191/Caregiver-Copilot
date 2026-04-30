"""v0 Agent Loop — single-model ReAct loop using GLM-4.5-Air via OpenRouter.

This is the simple precursor to the LangGraph-based agent (CC-029).
It loads all read + write tools, sends messages to the generator model,
and loops up to MAX_ITERATIONS executing any tool calls the model requests.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import get_context_tools, get_write_tools, set_session
from app.agent.tools.types import Tool
from app.core.config import get_settings
from app.providers.factory import get_generator_provider
from app.providers.types import ChatResponse, Message, ToolDefinition, ToolFunction

# Import all models so SQLAlchemy metadata is complete (FK resolution)
import app.models.care_recipient  # noqa: F401
import app.models.caregiver  # noqa: F401
import app.models.conversation  # noqa: F401
import app.models.document  # noqa: F401
import app.models.episode  # noqa: F401
import app.models.medication  # noqa: F401
import app.models.vital  # noqa: F401

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
_PROMPT_PATH = Path(__file__).parent / "prompts" / "v0_system.md"


class AgentResult(BaseModel):
    """Returned by run_agent — the final assistant reply plus audit info."""
    content: str
    tool_calls_log: list[dict[str, Any]]
    model_used: str
    tokens_input: int
    tokens_output: int
    latency_ms: int


def _load_system_prompt() -> str:
    """Read the v0 system prompt from disk."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _tools_to_definitions(tools: list[Tool]) -> list[ToolDefinition]:
    """Convert our Tool dataclass list into OpenAI ToolDefinition format."""
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
    """Build a name -> Tool lookup."""
    return {t.name: t for t in tools}


async def _execute_tool(tool: Tool, arguments: dict) -> str:
    """Call a tool function and return its result as a JSON string."""
    try:
        # Convert string UUIDs to uuid.UUID for care_recipient_id
        if "care_recipient_id" in arguments:
            arguments["care_recipient_id"] = uuid.UUID(arguments["care_recipient_id"])

        result = await tool.function(**arguments)

        # Pydantic BaseModel result — serialise to dict
        if hasattr(result, "model_dump"):
            return json.dumps(result.model_dump(), default=str)
        # List of Pydantic models
        if isinstance(result, list) and result and hasattr(result[0], "model_dump"):
            return json.dumps([r.model_dump() for r in result], default=str)
        # Empty list
        if isinstance(result, list) and not result:
            return json.dumps([])
        # Fallback
        return json.dumps(result, default=str)
    except Exception as e:
        logger.error("Tool %s failed: %s", tool.name, e)
        return json.dumps({"error": str(e)})


async def run_agent(
    care_recipient_id: uuid.UUID,
    user_message: str,
    db: AsyncSession,
    thread_id: uuid.UUID | None = None,
) -> AgentResult:
    """Run the v0 ReAct agent loop.

    1. Inject the DB session into the tool ContextVar.
    2. Build system prompt + user message.
    3. Send to the generator model with all tools.
    4. Loop: execute tool calls → append results → send back.
    5. Return the final assistant content.
    """
    start = time.monotonic()
    settings = get_settings()

    # Bind session so tools can use it
    set_session(db)

    # Gather all tools
    all_tools = get_context_tools() + get_write_tools()
    tool_defs = _tools_to_definitions(all_tools)
    tool_map = _build_tool_map(all_tools)

    # Build initial messages
    system_prompt = _load_system_prompt()
    
    # Inject the care_recipient_id so the model knows which patient to query
    context_note = (
        f"\n\n## Current Session Context\n"
        f"You are assisting with care recipient ID: `{care_recipient_id}`.\n"
        f"Use this ID for ALL tool calls. Do NOT ask the user for this ID.\n"
        f"Start by calling `get_care_recipient_profile` and `get_active_medications` "
        f"with this ID to load context before responding."
    )
    
    messages: list[Message] = [
        Message(role="system", content=system_prompt + context_note),
        Message(role="user", content=user_message),
    ]

    # Track tool calls for audit
    all_tool_calls_log: list[dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0

    provider = get_generator_provider()
    model = settings.generator_model_name

    try:
        for iteration in range(MAX_ITERATIONS):
            logger.info("Agent loop iteration %d", iteration + 1)

            response: ChatResponse = await provider.chat_with_tools(
                messages=messages,
                model=model,
                tools=tool_defs,
            )

            total_input_tokens += response.usage.prompt_tokens
            total_output_tokens += response.usage.completion_tokens

            # No tool calls → model is done
            if not response.tool_calls:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                content = response.content or "I'm sorry, I couldn't generate a response."
                return AgentResult(
                    content=content,
                    tool_calls_log=all_tool_calls_log,
                    model_used=model,
                    tokens_input=total_input_tokens,
                    tokens_output=total_output_tokens,
                    latency_ms=elapsed_ms,
                )

            # Append the assistant message with tool_calls
            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            # Execute each tool call
            for tc in response.tool_calls:
                tool_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                # Save a JSON-safe copy before _execute_tool mutates UUIDs
                arguments_log = json.loads(json.dumps(arguments, default=str))

                tool = tool_map.get(tool_name)
                if tool is None:
                    result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                    logger.warning("Model called unknown tool: %s", tool_name)
                else:
                    result_str = await _execute_tool(tool, arguments)

                # Log for audit
                all_tool_calls_log.append({
                    "iteration": iteration + 1,
                    "tool_call_id": tc.id,
                    "tool_name": tool_name,
                    "arguments": arguments_log,
                    "result": result_str[:500],  # truncate for storage
                })

                # Append tool result message
                messages.append(
                    Message(
                        role="tool",
                        content=result_str,
                        tool_call_id=tc.id,
                    )
                )

        # If we hit MAX_ITERATIONS, return what we have
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Agent hit max iterations (%d)", MAX_ITERATIONS)
        return AgentResult(
            content=(
                "I apologize, but I'm having difficulty completing this request. "
                "Please try rephrasing your question or contact the care recipient's "
                "healthcare provider directly if this is urgent."
            ),
            tool_calls_log=all_tool_calls_log,
            model_used=model,
            tokens_input=total_input_tokens,
            tokens_output=total_output_tokens,
            latency_ms=elapsed_ms,
        )
    finally:
        await provider.aclose()
