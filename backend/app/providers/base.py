"""Abstract base class for all model providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.providers.types import ChatResponse, Message, ToolDefinition


class ModelProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[Message], model: str, **kwargs) -> ChatResponse:
        """Send a chat request and return a complete response."""
        ...

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition],
        **kwargs,
    ) -> ChatResponse:
        """Send a chat request with tool definitions; parse any tool calls in the response."""
        ...

    @abstractmethod
    async def chat_stream(
        self, messages: list[Message], model: str, **kwargs
    ) -> AsyncIterator[str]:
        """Stream a chat response, yielding incremental text tokens."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Embed a list of texts; returns one vector per text."""
        ...
