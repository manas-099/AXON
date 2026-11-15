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
    Concrete adapter for a self-hosted OpenAI-compatible LLM endpoint.
    Handles: generate(), stream(), retry logic, health tracking.
    Import via LLMFactory.create() — never instantiate directly.
    """

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            model_name = settings.my_llm.MODEL_NAME,
            provider   = "my_llm",
        )
        self._settings = settings.my_llm
        self._health   = _HealthState(self._settings.HEALTH_CHECK_COOLDOWN_SECONDS)
        self._logger.info(
            "llm_adapter_initialized",
            model   = self._model_name,
            api_url = self._settings.API_URL,
        )

    def generate(
        self,
        messages: list[ChatMessage],
        tools:    list[ToolSchema] | None = None,
    ) -> LLMResponse:
        """
        Send conversation to LLM. Retries on server errors.
        Raises LLMAdapterError after all retries exhausted.
        """
        if not self._health.is_available:
            raise LLMAdapterError("LLM endpoint in cooldown. Try again shortly.")

        payload = self._build_payload(messages, tools, stream=False)
        headers = self._build_headers()
        last_error: str | None = None
        start = time.monotonic()

        for attempt in range(1, self._settings.MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=self._settings.TIMEOUT_SECONDS) as client:
                    resp = client.post(self._settings.API_URL, headers=headers, json=payload)

                if resp.status_code >= 400:
                    last_error = f"http_{resp.status_code}"
                    if 400 <= resp.status_code < 500:
                        self._health.mark_failed()
                        break
                    if attempt < self._settings.MAX_RETRIES:
                        time.sleep(self._settings.RETRY_DELAY_SECONDS)
                    continue

                self._health.mark_healthy()
                return self._parse_response(resp.json())

            except httpx.TimeoutException:
                last_error = "timeout"
                self._health.mark_failed()
                if attempt < self._settings.MAX_RETRIES:
                    time.sleep(self._settings.RETRY_DELAY_SECONDS)

            except httpx.RequestError as e:
                last_error = str(e)
                self._health.mark_failed()
                if attempt < self._settings.MAX_RETRIES:
                    time.sleep(self._settings.RETRY_DELAY_SECONDS)

        self._logger.error(
            "llm_generate_failed",
            attempts   = self._settings.MAX_RETRIES,
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
            with httpx.Client(timeout=self._settings.TIMEOUT_SECONDS) as client:
                with client.stream("POST", self._settings.API_URL, headers=headers, json=payload) as response:
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
        return {
            "Content-Type" : "application/json",
            "Authorization": f"Bearer {self._settings.AUTH_TOKEN}",
        }

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
