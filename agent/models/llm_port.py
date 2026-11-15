from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generator

from agent.models.chat_message import ChatMessage
from agent.models.llm_response import LLMResponse, ToolSchema


class LLMPort(ABC):
    """
    Outbound port — defines what the application needs from any LLM.
    All LLM adapters must implement this interface.
    The domain and application layers import only this — never a concrete adapter.
    """

    @abstractmethod
    def generate(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> LLMResponse:
        """Send a conversation to the LLM and get a full response."""
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> Generator[str, None, None]:
        """Stream response tokens as they arrive."""
        ...
