from __future__ import annotations

from typing import Any

from agent.models.llm_response import ToolSchema
from agent.mcp_client import MCPClient
from agent.logger import get_logger


class ToolBridge:
    """
    Converts MCP tool definitions into ToolSchema objects the LLM understands,
    and executes tool calls by routing them back through MCPClient.

    Single responsibility: be the translator between MCP and LLM formats.

    Usage:
        bridge  = ToolBridge(mcp_client)
        schemas = bridge.get_schemas()          # pass to LLM
        result  = bridge.execute("read_file", {"path": "..."})
    """

    def __init__(self, mcp_client: MCPClient) -> None:
        self._client  = mcp_client
        self._logger  = get_logger(__name__)
        self._schemas : list[ToolSchema] = []

    @classmethod
    def create(cls) -> "ToolBridge":
        """Factory method: create ToolBridge with a fresh MCPClient."""
        return cls(mcp_client=MCPClient.create())

    def load(self) -> None:
        """
        Fetch tools from MCP server and convert to ToolSchema list.
        Call once at startup before passing schemas to the LLM.
        """
        raw_tools    = self._client.list_tools()
        self._schemas = [self._to_schema(t) for t in raw_tools]
        self._logger.info("tool_bridge_loaded", count=len(self._schemas))

    def get_schemas(self) -> list[ToolSchema]:
        """Return all tool schemas ready to pass to LLMAdapter.generate()."""
        return self._schemas

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """
        Execute a tool by name with the given arguments.
        Returns the tool result as a plain string.
        """
        self._logger.info("tool_bridge_execute", tool=name)
        return self._client.call_tool(name, arguments)

    @staticmethod
    def _to_schema(raw: dict[str, Any]) -> ToolSchema:
        """
        Convert one raw MCP tool dict to a ToolSchema.
        MCP inputSchema is already valid JSON Schema — use directly.
        """
        return ToolSchema(
            name        = raw["name"],
            description = raw.get("description", ""),
            parameters  = raw.get("inputSchema", {
                "type"      : "object",
                "properties": {},
            }),
        )
