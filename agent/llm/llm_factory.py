from __future__ import annotations

from agent.llm.base_llm_adapter import BaseLLMAdapter
from agent.llm.my_llm_adapter import LLMAdapter
from agent.logger import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """
    Creates and returns the correct LLM adapter instance.
    Application layer calls LLMFactory.create() once at startup.
    Never import LLMAdapter directly — always go through this factory.
    """

    @staticmethod
    def create() -> BaseLLMAdapter:
        """Factory method: instantiate and return the configured LLM adapter."""
        adapter = LLMAdapter()
        logger.info(
            "llm_factory_created",
            adapter  = adapter.__class__.__name__,
            provider = adapter.provider,
            model    = adapter.model_name,
        )
        return adapter
