from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import Client

from agent.config import get_settings
from agent.logger import get_logger


class MCPClient:
    """
    Wraps the FastMCP async Client for use from sync code.
    The LLMAdapter is sync; FastMCP Client is async.
    This class bridges the gap by running async calls in a managed event loop.

    Responsibilities:
      - Connect to the AXON MCP server process
      - Fetch the list of available tools
      - Execute a single tool call and return the result string

    Usage:
        client = MCPClient.create()
        tools  = client.list_tools()
        result = client.call_tool("read_file", {"path": "C:/..."})
    """

    def __init__(self, server_script: str) -> None:
        self._server_script = server_script
        self._logger        = get_logger(__name__)

    @classmethod
    def create(cls) -> "MCPClient":
        """Factory method: create MCPClient from settings."""
        settings = get_settings()
        return cls(server_script=settings.mcp.SERVER_SCRIPT)

    def list_tools(self) -> list[dict[str, Any]]:
        """
        Fetch and return all tools registered on the MCP server.
        Returns a list of dicts with keys: name, description, inputSchema.
        """
        return asyncio.run(self._async_list_tools())

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """
        Execute one tool on the MCP server and return the result as a string.
        Raises MCPClientError if the tool call fails.
        """
        return asyncio.run(self._async_call_tool(name, arguments))

    async def _async_list_tools(self) -> list[dict[str, Any]]:
        """Async: connect to MCP server and list tools."""
        async with Client(self._server_script) as client:
            tools = await client.list_tools()
            self._logger.info("mcp_tools_fetched", count=len(tools))
            return [
                {
                    "name"       : t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in tools
            ]

    async def _async_call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Async: connect to MCP server and execute one tool call."""
        self._logger.info("mcp_tool_calling", tool=name, arguments=arguments)
        async with Client(self._server_script) as client:
            result = await client.call_tool(name, arguments)
            # FastMCP CallToolResult has .content list of content blocks
            blocks = result.content if hasattr(result, "content") else (result if isinstance(result, list) else [])
            text = ""
            for block in blocks:
                if hasattr(block, "text"):
                    text += block.text
            self._logger.info("mcp_tool_result", tool=name, length=len(text))
            return text


class MCPClientError(Exception):
    """Raised when an MCP tool call fails."""
