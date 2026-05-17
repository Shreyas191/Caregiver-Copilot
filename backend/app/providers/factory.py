"""Provider factory — constructs role-specific ModelProvider instances from config.

Each role (router, generator, verifier, embeddings) has its own BASE_URL,
API_KEY, and MODEL_NAME so the serving layer can differ per role.
"""

from app.core.config import get_settings
from app.providers.base import ModelProvider
from app.providers.openai_compatible import OpenAICompatibleProvider

# OpenRouter attribution headers (required by their ToS)
_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://caregiver-copilot.dev",
    "X-Title": "Caregiver Co-Pilot",
}


def _is_openrouter(url: str) -> bool:
    return "openrouter.ai" in url


def _make_provider(
    base_url: str,
    api_key: str,
    fallback_models: list[str] | None = None,
) -> ModelProvider:
    headers = _OPENROUTER_HEADERS if _is_openrouter(base_url) else {}
    return OpenAICompatibleProvider(
        base_url=base_url,
        api_key=api_key,
        default_headers=headers,
        fallback_models=fallback_models if _is_openrouter(base_url) else None,
    )


def get_router_provider() -> ModelProvider:
    s = get_settings()
    return _make_provider(s.router_base_url, s.router_api_key)


def get_generator_provider() -> ModelProvider:
    s = get_settings()
    return _make_provider(s.generator_base_url, s.generator_api_key, s.generator_fallback_models)


def get_verifier_provider() -> ModelProvider:
    s = get_settings()
    return _make_provider(s.verifier_base_url, s.verifier_api_key, s.verifier_fallback_models)


def get_embedding_provider() -> ModelProvider:
    s = get_settings()
    return _make_provider(s.embedding_base_url, s.embedding_api_key)


def get_provider(name: str) -> ModelProvider:
    """Legacy helper — returns an Ollama provider by name.

    Prefer the role-specific helpers above for new code.
    'together' and 'vllm' are planned for CC-054 / CC-055.
    """
    name = name.lower()
    if name == "ollama":
        from app.providers.ollama import OllamaProvider

        return OllamaProvider()
    if name in ("together", "vllm"):
        raise NotImplementedError(f"Provider '{name}' is not yet implemented.")
    raise ValueError(f"Unknown provider: '{name}'")
