"""OllamaProvider: thin configuration wrapper around OpenAICompatibleProvider.

Configures the provider to point at the local Ollama /v1 endpoint with the
"ollama" placeholder API key that Ollama requires (but ignores).
"""

from app.providers.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """Pre-configured OpenAICompatibleProvider for a local Ollama instance."""

    def __init__(self, base_url: str = "http://localhost:11434/v1", timeout: float = 120.0):
        super().__init__(base_url=base_url, api_key="ollama", timeout=timeout)
