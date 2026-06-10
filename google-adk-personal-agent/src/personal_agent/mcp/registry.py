"""MCP discovery and sanitized AgentGuard manifest generation."""

from __future__ import annotations

from typing import Any

from agentguard_sdk import ToolManifest

from personal_agent.mcp.config import McpServerConfig


class McpRegistry:
    def __init__(self, servers: list[McpServerConfig]):
        self.servers = servers
        self._manifests: dict[str, ToolManifest] = {}

    def ready_servers(self) -> list[McpServerConfig]:
        return [server for server in self.servers if server.ready]

    def register_tool(self, server: McpServerConfig, tool: Any) -> ToolManifest:
        raw_tool = getattr(tool, "_mcp_tool", tool)
        raw_name = str(getattr(raw_tool, "name", None) or getattr(tool, "name", "unknown"))
        schema = (
            getattr(raw_tool, "inputSchema", None)
            or getattr(raw_tool, "input_schema", None)
            or {}
        )
        if hasattr(schema, "model_dump"):
            schema = schema.model_dump(mode="json")
        annotations = getattr(raw_tool, "annotations", None) or {}
        if hasattr(annotations, "model_dump"):
            annotations = annotations.model_dump(mode="json")
        manifest = ToolManifest(
            name=server.prefixed_tool_name(raw_name),
            source_name=raw_name,
            provider=server.id,
            framework="google_adk",
            transport="mcp",
            description=str(getattr(raw_tool, "description", None) or ""),
            input_schema=schema if isinstance(schema, dict) else {},
            annotations=annotations if isinstance(annotations, dict) else {},
            metadata_provenance=["mcp_discovery"],
        )
        self._manifests[manifest.name] = manifest
        return manifest

    def manifests(self) -> list[ToolManifest]:
        return list(self._manifests.values())
