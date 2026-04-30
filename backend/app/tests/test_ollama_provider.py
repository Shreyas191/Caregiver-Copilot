"""Provider integration tests.

Two test groups:
  1. Local Ollama  — router (qwen2.5:7b) and embeddings (bge-m3:latest).
     Skipped if Ollama is not running.
  2. OpenRouter    — generator (z-ai/glm-4.5-air:free) and verifier
     (meta-llama/llama-3.3-70b-instruct:free).
     Skipped if OPENROUTER_API_KEY env var is not set.

Run all tests:
    pytest app/tests/test_ollama_provider.py -v

Run only local tests:
    pytest app/tests/test_ollama_provider.py -v -k "ollama"

Run only OpenRouter tests:
    pytest app/tests/test_ollama_provider.py -v -k "openrouter"
"""

import json
import os

import httpx
import pytest

from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.types import Message, ToolDefinition, ToolFunction

OLLAMA_URL = "http://localhost:11434/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"

ROUTER_MODEL = "qwen2.5:7b"
EMBEDDING_MODEL = "bge-m3:latest"
GENERATOR_MODEL = "z-ai/glm-4.5-air:free"
VERIFIER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


# ------------------------------------------------------------------
# Skip conditions
# ------------------------------------------------------------------


def _ollama_available() -> bool:
    try:
        httpx.get("http://localhost:11434/api/tags", timeout=3).raise_for_status()
        return True
    except Exception:
        return False


def _openrouter_key() -> str:
    """Return an OpenRouter key from the most common env var names."""
    return (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("GENERATOR_API_KEY")
        or ""
    )


skip_no_ollama = pytest.mark.skipif(
    not _ollama_available(), reason="Ollama not running at localhost:11434"
)

skip_no_openrouter = pytest.mark.skipif(
    not _openrouter_key(),
    reason="OPENROUTER_API_KEY not set — set it to run OpenRouter tests",
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def ollama_provider() -> OllamaProvider:
    return OllamaProvider(base_url=OLLAMA_URL)


@pytest.fixture
def openrouter_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=OPENROUTER_URL,
        api_key=_openrouter_key() or "no-key",
        default_headers={
            "HTTP-Referer": "https://caregiver-copilot.dev",
            "X-Title": "Caregiver Co-Pilot",
        },
    )


# ------------------------------------------------------------------
# Tool definition shared by tool-call tests
# ------------------------------------------------------------------

_WEATHER_TOOL = ToolDefinition(
    function=ToolFunction(
        name="get_weather",
        description="Get the current weather for a given city.",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"},
            },
            "required": ["city"],
        },
    )
)


# ==================================================================
# Local Ollama tests
# ==================================================================


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_chat_returns_string(ollama_provider: OllamaProvider) -> None:
    response = await ollama_provider.chat(
        messages=[Message(role="user", content="Reply with exactly the word OK and nothing else.")],
        model=ROUTER_MODEL,
    )
    assert response.content is not None
    assert len(response.content) > 0


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_chat_usage_populated(ollama_provider: OllamaProvider) -> None:
    response = await ollama_provider.chat(
        messages=[Message(role="user", content="Say hello.")],
        model=ROUTER_MODEL,
    )
    assert response.usage.total_tokens > 0


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_tool_call_parsed(ollama_provider: OllamaProvider) -> None:
    response = await ollama_provider.chat_with_tools(
        messages=[Message(role="user", content="What is the weather in Paris right now?")],
        model=ROUTER_MODEL,
        tools=[_WEATHER_TOOL],
    )
    assert len(response.tool_calls) > 0, "Expected at least one tool call"
    tc = response.tool_calls[0]
    assert tc.function.name == "get_weather"
    args = json.loads(tc.function.arguments)
    assert "city" in args


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_tool_call_arguments_valid_json(ollama_provider: OllamaProvider) -> None:
    response = await ollama_provider.chat_with_tools(
        messages=[Message(role="user", content="What is the weather in Tokyo?")],
        model=ROUTER_MODEL,
        tools=[_WEATHER_TOOL],
    )
    for tc in response.tool_calls:
        json.loads(tc.function.arguments)  # must not raise


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_stream_yields_tokens(ollama_provider: OllamaProvider) -> None:
    tokens: list[str] = []
    async for token in ollama_provider.chat_stream(
        messages=[Message(role="user", content="Count from 1 to 5.")],
        model=ROUTER_MODEL,
    ):
        tokens.append(token)
    assert len(tokens) > 0
    assert len("".join(tokens)) > 0


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_embed_1024_dim(ollama_provider: OllamaProvider) -> None:
    vectors = await ollama_provider.embed(texts=["This is a test sentence."], model=EMBEDDING_MODEL)
    assert len(vectors) == 1
    assert len(vectors[0]) == 1024


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_embed_batch(ollama_provider: OllamaProvider) -> None:
    texts = ["First sentence.", "Second sentence.", "Third sentence."]
    vectors = await ollama_provider.embed(texts=texts, model=EMBEDDING_MODEL)
    assert len(vectors) == len(texts)
    for v in vectors:
        assert len(v) == 1024


@skip_no_ollama
@pytest.mark.asyncio
async def test_ollama_embed_deterministic(ollama_provider: OllamaProvider) -> None:
    text = "Caregiver Co-Pilot embedding test."
    v1 = await ollama_provider.embed(texts=[text], model=EMBEDDING_MODEL)
    v2 = await ollama_provider.embed(texts=[text], model=EMBEDDING_MODEL)
    assert v1[0] == v2[0]


# ==================================================================
# OpenRouter tests (require OPENROUTER_API_KEY)
# ==================================================================


@skip_no_openrouter
@pytest.mark.asyncio
async def test_openrouter_glm_chat(openrouter_provider: OpenAICompatibleProvider) -> None:
    response = await openrouter_provider.chat(
        messages=[Message(role="user", content="Reply with exactly the word OK and nothing else.")],
        model=GENERATOR_MODEL,
    )
    assert response.content is not None
    assert len(response.content) > 0


@skip_no_openrouter
@pytest.mark.asyncio
async def test_openrouter_glm_tool_call(openrouter_provider: OpenAICompatibleProvider) -> None:
    response = await openrouter_provider.chat_with_tools(
        messages=[Message(role="user", content="What is the weather in London right now?")],
        model=GENERATOR_MODEL,
        tools=[_WEATHER_TOOL],
    )
    assert len(response.tool_calls) > 0, "GLM-4.5-Air should issue a tool call"
    tc = response.tool_calls[0]
    assert tc.function.name == "get_weather"
    args = json.loads(tc.function.arguments)
    assert "city" in args


@skip_no_openrouter
@pytest.mark.asyncio
async def test_openrouter_llama_chat(openrouter_provider: OpenAICompatibleProvider) -> None:
    response = await openrouter_provider.chat(
        messages=[
            Message(role="user", content="Reply with exactly the word VERIFIED and nothing else.")
        ],
        model=VERIFIER_MODEL,
    )
    assert response.content is not None
    assert len(response.content) > 0


@skip_no_openrouter
@pytest.mark.asyncio
async def test_openrouter_glm_stream(openrouter_provider: OpenAICompatibleProvider) -> None:
    tokens: list[str] = []
    async for token in openrouter_provider.chat_stream(
        messages=[Message(role="user", content="Count from 1 to 3.")],
        model=GENERATOR_MODEL,
    ):
        tokens.append(token)
    assert len(tokens) > 0
