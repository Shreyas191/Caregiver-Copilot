"""Claude provider using the Anthropic SDK (CC-047)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import anthropic

from app.providers.base import ModelProvider
from app.providers.types import (
    ChatResponse,
    Message,
    ToolCall,
    ToolCallFunction,
    ToolDefinition,
    UsageInfo,
)

logger = logging.getLogger(__name__)


class ClaudeProvider(ModelProvider):
    """ModelProvider backed by the Anthropic Messages API."""

    def __init__(self, api_key: str, timeout: float = 120.0):
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)

    # ------------------------------------------------------------------
    # Message format conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _split_system(messages: list[Message]) -> tuple[str | None, list[Message]]:
        """Separate system messages; return (combined_system_text, remaining)."""
        system_parts: list[str] = []
        others: list[Message] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content or "")
            else:
                others.append(m)
        return "\n\n".join(system_parts) or None, others

    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
        """Convert our Message objects to the Anthropic API format.

        Tool results are grouped into a single user message (Anthropic requirement).
        """
        result: list[dict] = []
        i = 0
        while i < len(messages):
            m = messages[i]
            if m.role == "tool":
                # Batch all consecutive tool results into one user message
                blocks: list[dict] = []
                while i < len(messages) and messages[i].role == "tool":
                    tm = messages[i]
                    blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tm.tool_call_id or "",
                        "content": tm.content or "",
                    })
                    i += 1
                result.append({"role": "user", "content": blocks})
            elif m.role == "assistant" and m.tool_calls:
                content: list[dict] = []
                if m.content:
                    content.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    try:
                        input_dict = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, TypeError):
                        input_dict = {}
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": input_dict,
                    })
                result.append({"role": "assistant", "content": content})
                i += 1
            elif m.role in ("user", "assistant"):
                result.append({"role": m.role, "content": m.content or ""})
                i += 1
            else:
                i += 1
        return result

    @staticmethod
    def _tools_to_anthropic(tools: list[ToolDefinition]) -> list[dict]:
        return [
            {
                "name": t.function.name,
                "description": t.function.description,
                "input_schema": t.function.parameters,
            }
            for t in tools
        ]

    def _parse_response(self, response) -> ChatResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        function=ToolCallFunction(
                            name=block.name,
                            arguments=json.dumps(block.input),
                        ),
                    )
                )
        return ChatResponse(
            content="\n".join(text_parts) or None,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason,
            usage=UsageInfo(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            ),
        )

    def _build_kwargs(self, messages: list[Message], model: str, **kwargs) -> dict:
        system, msgs = self._split_system(messages)
        kw: dict[str, Any] = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": self._to_anthropic_messages(msgs),
        }
        if system:
            kw["system"] = system
        return kw

    # ------------------------------------------------------------------
    # ModelProvider interface
    # ------------------------------------------------------------------

    async def chat(self, messages: list[Message], model: str, **kwargs) -> ChatResponse:
        kw = self._build_kwargs(messages, model, **kwargs)
        response = await self._client.messages.create(**kw)
        return self._parse_response(response)

    async def chat_with_tools(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition],
        **kwargs,
    ) -> ChatResponse:
        kw = self._build_kwargs(messages, model, **kwargs)
        kw["tools"] = self._tools_to_anthropic(tools)
        response = await self._client.messages.create(**kw)
        return self._parse_response(response)

    async def chat_stream(
        self, messages: list[Message], model: str, **kwargs
    ) -> AsyncIterator[str]:
        kw = self._build_kwargs(messages, model, **kwargs)
        async with self._client.messages.stream(**kw) as stream:
            async for text in stream.text_stream:
                yield text

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError("Claude does not provide an embedding API.")

    async def aclose(self) -> None:
        await self._client.close()
