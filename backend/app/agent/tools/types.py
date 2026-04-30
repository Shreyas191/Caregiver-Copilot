"""Tool type definition used by the agent layer."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Tool:
    """Describes one agent tool: its identity, schema, and callable implementation."""

    name: str
    description: str
    input_schema: dict  # JSON Schema — maps directly to OpenAI function parameters
    function: Callable  # async callable; signature must match input_schema properties
