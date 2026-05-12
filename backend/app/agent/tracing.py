"""CC-049: Langfuse tracing helpers for LangGraph nodes."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

_langfuse_client = None
_enabled = False


def _get_client():
    global _langfuse_client, _enabled
    if _langfuse_client is not None:
        return _langfuse_client

    try:
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            _enabled = False
            return None

        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        _enabled = True
        logger.info("Langfuse tracing enabled at %s", settings.langfuse_host)
    except Exception as e:
        logger.debug("Langfuse not available: %s", e)
        _enabled = False
        _langfuse_client = None

    return _langfuse_client


def trace_node(node_name: str):
    """Decorator that wraps an async LangGraph node function with a Langfuse span."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(state: Any, *args, **kwargs) -> Any:
            client = _get_client()
            thread_id = str(state.get("thread_id") or "no-thread")
            care_id = str(state.get("care_recipient_id") or "unknown")

            if not client or not _enabled:
                return await fn(state, *args, **kwargs)

            trace = client.trace(
                name=f"caregiver-agent/{thread_id}",
                session_id=thread_id,
                user_id=state.get("caregiver_clerk_id", "unknown"),
                metadata={"care_recipient_id": care_id},
            )
            span = trace.span(
                name=node_name,
                input={"intent": state.get("intent"), "message_count": len(state.get("messages", []))},
            )

            start = time.monotonic()
            try:
                result = await fn(state, *args, **kwargs)
                span.end(
                    output=_safe_output(result),
                    level="DEFAULT",
                )
                return result
            except Exception as e:
                span.end(
                    output={"error": str(e)},
                    level="ERROR",
                )
                raise
            finally:
                latency = int((time.monotonic() - start) * 1000)
                logger.debug("Node %s completed in %dms", node_name, latency)

        return wrapper
    return decorator


def trace_llm_call(
    trace,
    model: str,
    messages: list,
    response_content: str | None,
    tool_calls: list,
    usage: Any | None,
    node_name: str,
) -> None:
    """Log an LLM generation event to an existing Langfuse trace."""
    if not trace or not _enabled:
        return
    try:
        trace.generation(
            name=f"{node_name}/llm",
            model=model,
            input=messages,
            output=response_content or "",
            usage={
                "promptTokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "completionTokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                "totalTokens": getattr(usage, "total_tokens", 0) if usage else 0,
            },
            metadata={"tool_calls_count": len(tool_calls)},
        )
    except Exception as e:
        logger.debug("Langfuse generation log failed: %s", e)


def _safe_output(result: Any) -> dict:
    if isinstance(result, dict):
        return {k: str(v)[:200] for k, v in result.items()}
    return {"result": str(result)[:200]}
