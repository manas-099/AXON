from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TokenUsage:
    """Token counts returned by the LLM API."""
    input_tokens:  int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ToolSchema:
    """
    Describes one tool the LLM can call.
    Passed to generate() so the LLM knows what tools exist.
    'parameters' is a JSON Schema dict describing the tool's arguments.
    """
    name:        str
    description: str
    parameters:  dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """
    Full response from one LLM generate() call.
    Either has text content, tool_calls, or both.
    Check has_tool_calls before reading tool_calls.
    """
    content:    str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model:      str                  = ""
    usage:      TokenUsage | None    = None

    @property
    def has_tool_calls(self) -> bool:
        """True if LLM wants to invoke one or more tools."""
        return len(self.tool_calls) > 0
