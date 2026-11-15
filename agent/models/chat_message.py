from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """Valid roles in a conversation turn."""
    SYSTEM    = "system"
    USER      = "user"
    ASSISTANT = "assistant"
    TOOL      = "tool"


@dataclass
class ChatMessage:
    """
    A single message in the conversation history.
    Covers all four roles: system, user, assistant, tool.
    Tool messages carry tool_call_id to link back to the assistant's call.
    Assistant messages may carry tool_calls when the LLM wants to invoke tools.
    """
    role:         MessageRole
    content:      str
    tool_call_id: str                    = ""
    tool_calls:   list[dict[str, Any]]   = field(default_factory=list)

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        """Factory: create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        """Factory: create a user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str, tool_calls: list[dict[str, Any]] | None = None) -> "ChatMessage":
        """Factory: create an assistant message, optionally with tool calls."""
        return cls(
            role       = MessageRole.ASSISTANT,
            content    = content,
            tool_calls = tool_calls or [],
        )

    @classmethod
    def tool_result(cls, tool_call_id: str, content: str) -> "ChatMessage":
        """Factory: create a tool result message."""
        return cls(
            role         = MessageRole.TOOL,
            content      = content,
            tool_call_id = tool_call_id,
        )
