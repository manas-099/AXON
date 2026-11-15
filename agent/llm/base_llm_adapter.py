from __future__ import annotations
from abc import abstractmethod
from typing import Generator

from agent.models.chat_message import ChatMessage
from agent.models.llm_response import LLMResponse, ToolSchema
from agent.models.llm_port import LLMPort
from agent.logger import get_logger


class BaseLLMAdapter(LLMPort):
    """
    Abstract base for all LLM adapters.
    Provides: logger, tool registry, token counter.
    Subclasses must implement: generate(), stream().
    """

    def __init__(self, model_name: str, provider: str) -> None:
        self._model_name     = model_name
        self._provider       = provider
        self._logger         = get_logger(self.__class__.__module__)
        self._tool_registry: dict[str, ToolSchema] = {}

    def register_tools(self, tools: list[ToolSchema]) -> None:
        """Register tool schemas so the LLM knows what tools exist."""
        for tool in tools:
            self._tool_registry[tool.name] = tool
        self._logger.info(
            "tools_registered",
            count      = len(tools),
            tool_names = [t.name for t in tools],
        )

    def get_tool_schemas(self) -> list[ToolSchema]:
        """Return all registered tool schemas."""
        return list(self._tool_registry.values())

    def count_tokens(self, messages: list[ChatMessage]) -> int:
        """Estimate token count — 1 token ≈ 4 chars. No API call needed."""
        return sum(len(m.content) for m in messages) // 4

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider(self) -> str:
        return self._provider

    @abstractmethod
    def generate(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> LLMResponse: ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> Generator[str, None, None]: ...
