from __future__ import annotations

import json
import time
from typing import Any, Generator

import httpx

from agent.config import get_settings
from agent.models.chat_message import ChatMessage, MessageRole
from agent.models.llm_response import LLMResponse, TokenUsage, ToolSchema
from agent.llm.base_llm_adapter import BaseLLMAdapter


def _to_api_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    """Convert domain ChatMessage list to OpenAI-compatible API format."""
    result = []
    for msg in messages:
        if msg.role == MessageRole.TOOL:
            result.append({
                "role"        : "tool",
                "content"     : msg.content,
                "tool_call_id": msg.tool_call_id,
            })
        elif msg.role == MessageRole.ASSISTANT and msg.tool_calls:
            result.append({
                "role"      : "assistant",
                "content"   : msg.content or None,
                "tool_calls": [
                    {
                        "id"      : tc["id"],
                        "type"    : "function",
                        "function": {
                            "name"     : tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })
        else:
            result.append({"role": msg.role.value, "content": msg.content})
    return result


def _to_api_tools(tools: list[ToolSchema]) -> list[dict[str, Any]]:
    """Convert ToolSchema list to OpenAI function-calling format."""
    return [
        {
            "type"    : "function",
            "function": {
                "name"       : t.name,
                "description": t.description,
                "parameters" : t.parameters,
            },
        }
        for t in tools
    ]


def _parse_tool_calls(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse raw API tool_calls into domain format."""
    parsed = []
    for tc in raw:
        try:
            arguments = json.loads(tc["function"]["arguments"])
        except (json.JSONDecodeError, KeyError):
            arguments = {}
        parsed.append({
            "name"     : tc["function"]["name"],
            "arguments": arguments,
            "id"       : tc.get("id", ""),
        })
    return parsed


class _HealthState:
    """
    Tracks whether the LLM endpoint is currently reachable.
    Prevents hammering a down server — uses cooldown before retrying.
    """

    def __init__(self, cooldown_seconds: int) -> None:
        self._healthy          = True
        self._last_failed_at   = 0.0
        self._cooldown_seconds = cooldown_seconds

    @property
    def is_available(self) -> bool:
        if self._healthy:
            return True
        return time.monotonic() - self._last_failed_at > self._cooldown_seconds

    def mark_healthy(self) -> None:
        self._healthy = True

    def mark_failed(self) -> None:
        self._healthy        = False
        self._last_failed_at = time.monotonic()


class LLMAdapterError(Exception):
    """Raised when LLMAdapter fails after all retries."""


class LLMAdapter(BaseLLMAdapter):
    """
    Concrete adapter for an OpenAI-compatible LLM endpoint with automatic fallback.
    If the primary LLM (e.g. Groq) encounters an error, it seamlessly switches to
    the configured backup LLM (e.g. OpenRouter) so execution is never disrupted.
    """

    def register_tools(self, tools: list[ToolSchema]) -> None:
        """Register tools with both primary and backup adapters."""
        super().register_tools(tools)
        if self._backup_adapter:
            self._backup_adapter.register_tools(tools)

    def __init__(
        self,
        api_url: str | None = None,
        auth_token: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int = 60,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
        provider: str = "my_llm",
    ) -> None:
        settings = get_settings()
        target_model = model_name or settings.my_llm.MODEL_NAME
        super().__init__(model_name=target_model, provider=provider)
        
        self._api_url = api_url or settings.my_llm.API_URL
        self._auth_token = auth_token or settings.my_llm.AUTH_TOKEN
        self._timeout_seconds = timeout_seconds if api_url else settings.my_llm.TIMEOUT_SECONDS
        self._max_retries = max_retries if api_url else settings.my_llm.MAX_RETRIES
        self._retry_delay_seconds = retry_delay_seconds if api_url else settings.my_llm.RETRY_DELAY_SECONDS
        self._health = _HealthState(settings.my_llm.HEALTH_CHECK_COOLDOWN_SECONDS)

        # Initialize backup adapter if enabled
        self._backup_adapter: LLMAdapter | None = None
        if provider != "backup_llm" and settings.backup_llm.ENABLED and settings.backup_llm.AUTH_TOKEN:
            self._backup_adapter = LLMAdapter(
                api_url=settings.backup_llm.API_URL,
                auth_token=settings.backup_llm.AUTH_TOKEN,
                model_name=settings.backup_llm.MODEL_NAME,
                timeout_seconds=settings.backup_llm.TIMEOUT_SECONDS,
                max_retries=settings.backup_llm.MAX_RETRIES,
                retry_delay_seconds=settings.backup_llm.RETRY_DELAY_SECONDS,
                provider="backup_llm",
            )
            self._logger.info(
                "backup_llm_configured",
                model=settings.backup_llm.MODEL_NAME,
                api_url=settings.backup_llm.API_URL,
            )

        self._logger.info(
            "llm_adapter_initialized",
            model=self._model_name,
            api_url=self._api_url,
        )

    def generate(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> LLMResponse:
        """
        Send conversation to LLM. Retries on server errors.
        If primary fails and a backup adapter is configured, falls back automatically.
        """
        try:
            return self._execute_generate(messages, tools)
        except Exception as e:
            if self._backup_adapter:
                self._logger.warning(
                    "primary_llm_failed_switching_to_backup",
                    error=str(e),
                    backup_model=self._backup_adapter.model_name,
                )
                return self._backup_adapter.generate(messages, tools)
            raise

    def _execute_generate(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> LLMResponse:
        if not self._health.is_available:
            raise LLMAdapterError("LLM endpoint in cooldown. Try again shortly.")

        payload = self._build_payload(messages, tools, stream=False)
        headers = self._build_headers()
        last_error: str | None = None
        start = time.monotonic()

        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    resp = client.post(self._api_url, headers=headers, json=payload)

                if resp.status_code >= 400:
                    last_error = f"http_{resp.status_code}: {resp.text[:200]}"
                    if 400 <= resp.status_code < 500:
                        self._health.mark_failed()
                        break
                    if attempt < self._max_retries:
                        time.sleep(self._retry_delay_seconds)
                    continue

                self._health.mark_healthy()
                return self._parse_response(resp.json())

            except httpx.TimeoutException:
                last_error = "timeout"
                self._health.mark_failed()
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay_seconds)

            except httpx.RequestError as e:
                last_error = str(e)
                self._health.mark_failed()
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay_seconds)

        self._logger.error(
            "llm_generate_failed",
            attempts   = self._max_retries,
            last_error = last_error,
            duration   = round(time.monotonic() - start, 3),
        )
        raise LLMAdapterError(f"LLMAdapter failed after retries: {last_error}")

    def stream(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> Generator[str, None, None]:
        """Stream response tokens. Tool calls not supported in stream mode."""
        payload = self._build_payload(messages, tools, stream=True)
        headers = self._build_headers()
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                with client.stream("POST", self._api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        chunk = self._parse_stream_chunk(line)
                        if chunk:
                            yield chunk
        except httpx.TimeoutException as e:
            raise LLMAdapterError(f"Stream timed out: {e}")
        except httpx.RequestError as e:
            raise LLMAdapterError(f"Stream request failed: {e}")

    def _build_payload(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None,
        stream:   bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model"      : self._model_name,
            "messages"   : _to_api_messages(messages),
            "temperature": 0.0,
            "max_tokens" : 4096,
            "stream"     : stream,
        }
        if tools:
            payload["tools"]       = _to_api_tools(tools)
            payload["tool_choice"] = "auto"
        return payload

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type" : "application/json",
            "Authorization": f"Bearer {self._auth_token}",
        }
        if "openrouter.ai" in self._api_url:
            headers["HTTP-Referer"] = "https://github.com/manas-099/AXON"
            headers["X-Title"] = "AXON File System Agent"
        return headers

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Parse raw API JSON into LLMResponse domain object."""
        choice     = data["choices"][0]
        message    = choice["message"]
        content    = message.get("content") or ""
        tool_calls = []
        if raw_tools := message.get("tool_calls"):
            tool_calls = _parse_tool_calls(raw_tools)
        usage = None
        if raw_usage := data.get("usage"):
            usage = TokenUsage(
                input_tokens  = raw_usage.get("prompt_tokens", 0),
                output_tokens = raw_usage.get("completion_tokens", 0),
            )
        return LLMResponse(
            content    = content,
            tool_calls = tool_calls,
            model      = data.get("model", self._model_name),
            usage      = usage,
        )

    def _parse_stream_chunk(self, line: str) -> str | None:
        """Parse one SSE line from a streaming response."""
        line = line.strip()
        if not line or not line.startswith("data:"):
            return None
        data_str = line[len("data:"):].strip()
        if data_str == "[DONE]":
            return None
        try:
            data  = json.loads(data_str)
            delta = data["choices"][0]["delta"]
            return delta.get("content") or None
        except (json.JSONDecodeError, KeyError, IndexError):
            return None
