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
_MAX_ATTEMPTS = 4
_BASE_DELAY = 1.0


class OpenAICompatibleProvider(ModelProvider):
    """
    ModelProvider that works with any OpenAI-compatible HTTP endpoint.

    Pass base_url pointing to the /v1 prefix (e.g. "http://localhost:11434/v1"
    for Ollama, "https://openrouter.ai/api/v1" for OpenRouter).

    fallback_models: tried in order via OpenRouter's `models` array when the
    primary model is rate-limited. Ignored for non-OpenRouter endpoints.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        default_headers: dict[str, str] | None = None,
        timeout: float = 120.0,
        fallback_models: list[str] | None = None,
    ):
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "placeholder",
            default_headers=default_headers or {},
            timeout=timeout,
        )
        self._fallback_models = fallback_models or []

    # ------------------------------------------------------------------
    # Retry helper — exponential backoff, up to _MAX_ATTEMPTS
    # ------------------------------------------------------------------

    @staticmethod
    def _retry_after(e: openai.APIStatusError) -> float:
        try:
            header = e.response.headers.get("retry-after") or e.response.headers.get("Retry-After")
            if header:
                return float(header)
        except Exception:
            pass
        return _BASE_DELAY

    async def _with_backoff(self, coro_fn):
        """Exponential backoff: 1s → 2s → 4s across up to _MAX_ATTEMPTS attempts."""
        delay = _BASE_DELAY
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await coro_fn()
            except openai.RateLimitError as e:
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
                wait = max(self._retry_after(e), delay)
                logger.warning(
                    "Rate-limited (attempt %d/%d); retrying in %.1fs", attempt + 1, _MAX_ATTEMPTS, wait
                )
                await asyncio.sleep(wait)
                delay *= 2
            except openai.APIStatusError as e:
                if e.status_code not in _RETRY_STATUSES or attempt == _MAX_ATTEMPTS - 1:
                    raise
                wait = max(self._retry_after(e), delay)
                logger.warning(
                    "Provider %d (attempt %d/%d); retrying in %.1fs", e.status_code, attempt + 1, _MAX_ATTEMPTS, wait
                )
                await asyncio.sleep(wait)
                delay *= 2

    def _models_extra(self, model: str) -> dict:
        """Build extra_body with OpenRouter fallback models array if configured.
        OpenRouter caps the models array at 3 items."""
        if not self._fallback_models:
            return {}
        return {"models": ([model] + self._fallback_models)[:3]}

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
        extra = self._models_extra(model)

        async def _call():
            return await self._client.chat.completions.create(
                model=model,
                messages=self._to_api_messages(messages),
                extra_body=extra or None,
                **kwargs,
            )

        response = await self._with_backoff(_call)
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
        extra = self._models_extra(model)

        async def _call():
            return await self._client.chat.completions.create(
                model=model,
                messages=api_messages,
                tools=api_tools,
                extra_body=extra or None,
                **kwargs,
            )

        response = await self._with_backoff(_call)
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
                    extra_body=extra or None,
                    **kwargs,
                )

            retry_response = await self._with_backoff(_retry_call)
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
        extra = self._models_extra(model)
        stream = await self._client.chat.completions.create(
            model=model,
            messages=self._to_api_messages(messages),
            stream=True,
            extra_body=extra or None,
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

        response = await self._with_backoff(_call)
        return [d.embedding for d in response.data]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        await self._client.close()
