from __future__ import annotations

from agent.models.chat_message import ChatMessage
from agent.logger import get_logger

_SYSTEM_PROMPT = """You are AXON — an autonomous file system agent.
You have tools to read, write, copy, move, search, and delete files and folders
on the user's Windows file system within configured allowed paths.

Rules:
1. Always call confirm_delete before any delete operation.
2. Use backup_file before overwriting important files.
3. Use undo_last if you make a mistake.
4. Only operate within allowed paths — never guess or construct paths.
5. If unsure whether a path exists, call file_exists first.
6. Be concise in your replies — one short sentence is enough after a tool call.
"""


class ChatSession:
    """
    Manages the conversation history for one AXON session.
    Prepends the system prompt automatically on creation.
    Provides methods to add messages and retrieve full history.

    Single responsibility: own and maintain the message list.
    """

    def __init__(self) -> None:
        self._logger   = get_logger(__name__)
        self._messages : list[ChatMessage] = [
            ChatMessage.system(_SYSTEM_PROMPT)
        ]

    def add_user(self, text: str) -> None:
        """Append a user message to history."""
        self._messages.append(ChatMessage.user(text))

    def add_assistant(self, text: str, tool_calls: list | None = None) -> None:
        """Append an assistant message to history."""
        self._messages.append(ChatMessage.assistant(text, tool_calls))

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        """Append a tool result message to history."""
        self._messages.append(ChatMessage.tool_result(tool_call_id, result))

    def get_history(self) -> list[ChatMessage]:
        """Return a copy of the full message history."""
        return list(self._messages)

    def clear(self) -> None:
        """Reset session, keeping only the system prompt."""
        self._messages = [ChatMessage.system(_SYSTEM_PROMPT)]
        self._logger.info("chat_session_cleared")

    @property
    def message_count(self) -> int:
        """Number of messages in history (including system prompt)."""
        return len(self._messages)
