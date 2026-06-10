"""Construct Google ADK MCP toolsets inside the agent process."""

from __future__ import annotations

from typing import Any

from personal_agent.mcp.config import McpServerConfig
from personal_agent.mcp.registry import McpRegistry


def build_mcp_toolsets(registry: McpRegistry) -> list[Any]:
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StdioConnectionParams,
        StreamableHTTPConnectionParams,
    )
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    from mcp import StdioServerParameters

    class ManifestMcpToolset(McpToolset):
        def __init__(self, *, server: McpServerConfig, **kwargs):
            self._server = server
            super().__init__(**kwargs)

        async def get_tools(self, readonly_context=None):
            tools = await super().get_tools(readonly_context)
            for tool in tools:
                registry.register_tool(self._server, tool)
            return tools

    toolsets = []
    for server in registry.ready_servers():
        if server.transport == "stdio":
            connection = StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=server.stdio_command or "",
                    args=list(server.stdio_args),
                    env=server.stdio_env or None,
                )
            )
        else:
            connection = StreamableHTTPConnectionParams(
                url=server.http_url or "",
                headers=server.http_headers or None,
            )
        toolsets.append(
            ManifestMcpToolset(
                server=server,
                connection_params=connection,
                tool_filter=None,
                tool_name_prefix=server.prefix,
            )
        )
    return toolsets
