"""OpenAICompatibleProvider: generic provider for any OpenAI-compatible endpoint.

Works against local Ollama, OpenRouter, vLLM, Together AI, or the real OpenAI API.
The openai Python SDK normalises tool-call format differences across providers.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import openai
from openai import AsyncOpenAI

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

_RETRY_STATUSES = {429, 500, 502, 503, 504}
_RETRY_DELAY = 2.0


class OpenAICompatibleProvider(ModelProvider):
    """
    ModelProvider that works with any OpenAI-compatible HTTP endpoint.

    Pass base_url pointing to the /v1 prefix (e.g. "http://localhost:11434/v1"
    for Ollama, "https://openrouter.ai/api/v1" for OpenRouter).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        default_headers: dict[str, str] | None = None,
        timeout: float = 120.0,
    ):
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "placeholder",
            default_headers=default_headers or {},
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def _retry_once(self, coro_fn, delay: float = _RETRY_DELAY):
        """Run coro_fn(); on 429 / 5xx retry once after `delay` seconds."""
        try:
            return await coro_fn()
        except openai.RateLimitError as e:
            logger.warning("Rate-limited by provider (429); retrying in %.1fs — %s", delay, e)
            await asyncio.sleep(delay)
            return await coro_fn()
        except openai.APIStatusError as e:
            if e.status_code in _RETRY_STATUSES:
                logger.warning(
                    "Provider returned %d; retrying in %.1fs — %s", e.status_code, delay, e
                )
                await asyncio.sleep(delay)
                return await coro_fn()
            raise

    # ------------------------------------------------------------------
    # Message serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def _to_api_messages(messages: list[Message]) -> list[dict]:
        result = []
        for m in messages:
            msg: dict = {"role": m.role}
            if m.tool_call_id:
                # Tool result message: role must be "tool"
                msg["tool_call_id"] = m.tool_call_id
                msg["content"] = m.content or ""
            elif m.tool_calls:
                # Assistant message that issued tool calls
                msg["content"] = m.content  # may be None
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in m.tool_calls
                ]
            else:
                msg["content"] = m.content or ""
            result.append(msg)
        return result

    # ------------------------------------------------------------------
    # Tool-call parsing with JSON validation
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_sdk_tool_calls(raw) -> tuple[list[ToolCall], bool]:
        """
        Convert SDK tool-call objects to our ToolCall type.
        Returns (parsed_calls, all_valid_json).
        """
        if not raw:
            return [], True
        parsed: list[ToolCall] = []
        all_valid = True
        for tc in raw:
            args_raw = tc.function.arguments or "{}"
            try:
                json.loads(args_raw)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Tool call '%s' has non-JSON arguments: %s", tc.function.name, args_raw
                )
                args_raw = "{}"
                all_valid = False
            parsed.append(
                ToolCall(
                    id=tc.id or "",
                    function=ToolCallFunction(name=tc.function.name, arguments=args_raw),
                )
            )
        return parsed, all_valid

    # ------------------------------------------------------------------
    # chat
    # ------------------------------------------------------------------

    async def chat(self, messages: list[Message], model: str, **kwargs) -> ChatResponse:
        async def _call():
            return await self._client.chat.completions.create(
                model=model,
                messages=self._to_api_messages(messages),
                **kwargs,
            )

        response = await self._retry_once(_call)
        choice = response.choices[0]
        usage = response.usage
        return ChatResponse(
            content=choice.message.content,
            tool_calls=[],
            finish_reason=choice.finish_reason,
            usage=UsageInfo(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
        )

    # ------------------------------------------------------------------
    # chat_with_tools
    # ------------------------------------------------------------------

    async def chat_with_tools(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition],
        **kwargs,
    ) -> ChatResponse:
        api_tools = [t.model_dump() for t in tools]
        api_messages = self._to_api_messages(messages)

        async def _call():
            return await self._client.chat.completions.create(
                model=model,
                messages=api_messages,
                tools=api_tools,
                **kwargs,
            )

        response = await self._retry_once(_call)
        choice = response.choices[0]
        tool_calls, all_valid = self._parse_sdk_tool_calls(choice.message.tool_calls)

        # Retry once if tool-call arguments were malformed JSON
        if choice.message.tool_calls and not all_valid:
            retry_messages = api_messages + [
                {
                    "role": "user",
                    "content": (
                        "Your previous response contained invalid JSON in the tool call "
                        "arguments. Please respond again with strictly valid JSON."
                    ),
                }
            ]

            async def _retry_call():
                return await self._client.chat.completions.create(
                    model=model,
                    messages=retry_messages,
                    tools=api_tools,
                    **kwargs,
                )

            retry_response = await self._retry_once(_retry_call)
            retry_choice = retry_response.choices[0]
            tool_calls, _ = self._parse_sdk_tool_calls(retry_choice.message.tool_calls)
            choice = retry_choice
            response = retry_response

        usage = response.usage
        return ChatResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=UsageInfo(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
        )

    # ------------------------------------------------------------------
    # chat_stream
    # ------------------------------------------------------------------

    async def chat_stream(
        self, messages: list[Message], model: str, **kwargs
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=model,
            messages=self._to_api_messages(messages),
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ------------------------------------------------------------------
    # embed
    # ------------------------------------------------------------------

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        async def _call():
            return await self._client.embeddings.create(model=model, input=texts)

        response = await self._retry_once(_call)
        return [d.embedding for d in response.data]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        await self._client.close()
