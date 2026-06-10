from __future__ import annotations

import json
import sys
import textwrap
from types import SimpleNamespace

import pytest

from agentguard.core.enums import ToolRiskLevel
from agentguard.integrations.google_adk import GoogleADKTraceSession
from agentguard.integrations.google_adk.mcp_registry import (
    McpRegistry,
    McpRegistryError,
)
from agentguard.tracing.trace_store import TraceStore


def test_registry_loads_stdio_and_http_servers_and_resolves_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_TOKEN", "secret-token-value")
    registry = _load_registry(
        tmp_path,
        """
        [[servers]]
        id = "local"
        prefix = "local"
        enabled = true
        transport = "stdio"

        [servers.stdio]
        command = "python"
        args = ["-m", "example"]

        [[servers]]
        id = "remote"
        prefix = "remote"
        enabled = true
        transport = "streamable_http"

        [servers.streamable_http]
        url = "https://example.test/mcp"
        headers = { Authorization = "Bearer ${MCP_TOKEN}" }
        """,
    )

    metadata = registry.metadata_for("local_lookup")
    assert metadata is not None
    assert metadata.category == "unknown"
    assert metadata.risk_level == ToolRiskLevel.READ_ONLY
    assert metadata.mcp_server == "local"
    assert metadata.provider == "mcp:local"
    assert metadata.action_tags == ("lookup",)

    unknown = registry.metadata_for("remote_new_tool")
    assert unknown is not None
    assert unknown.risk_level == ToolRiskLevel.HIGH_RISK
    assert unknown.requires_confirmation_by_default is True
    assert registry.redact("failed with secret-token-value") == "failed with [REDACTED]"


def test_adk_builds_one_unfiltered_toolset_per_ready_server(tmp_path):
    pytest.importorskip("google.adk")
    from examples.google_adk_agent.agent import _build_mcp_toolsets

    registry = _load_registry(
        tmp_path,
        f"""
        [[servers]]
        id = "local"
        prefix = "local"
        enabled = true
        transport = "stdio"
        [servers.stdio]
        command = {json.dumps(sys.executable)}

        [[servers]]
        id = "remote"
        prefix = "remote"
        enabled = true
        transport = "streamable_http"
        [servers.streamable_http]
        url = "https://example.test/mcp"
        """,
    )

    toolsets = _build_mcp_toolsets(registry)

    assert [toolset.tool_name_prefix for toolset in toolsets] == ["local", "remote"]
    assert all(toolset.tool_filter is None for toolset in toolsets)


def test_checked_in_workspace_server_uses_pinned_open_source_stdio_package():
    registry = McpRegistry.load("config/adk_mcp_servers.toml")
    workspace = next(server for server in registry.servers if server.id == "workspace")

    assert workspace.transport == "stdio"
    assert workspace.prefix == "workspace"
    assert workspace.stdio_command == "npx"
    assert "--package=github:gemini-cli-extensions/workspace#v0.0.8" in workspace.stdio_args
    assert "WORKSPACE_FEATURE_OVERRIDES" in workspace.stdio_env


def test_discovered_tools_infer_metadata_from_annotations_and_names(tmp_path):
    registry = _load_registry(
        tmp_path,
        """
        [[servers]]
        id = "project"
        prefix = "project"
        enabled = true
        transport = "stdio"
        [servers.stdio]
        command = "python"
        """,
    )
    server = registry.servers[0]

    read = registry.register_discovered_tool(
        server,
        _discovered_tool(
            "find_items",
            "Find project items.",
            read_only=True,
        ),
    )
    delete = registry.register_discovered_tool(
        server,
        _discovered_tool(
            "delete_item",
            "Delete one project item.",
            destructive=True,
        ),
    )
    ambiguous = registry.register_discovered_tool(
        server,
        _discovered_tool("process_item", "Process one project item."),
    )

    assert read.risk_level == ToolRiskLevel.READ_ONLY
    assert read.requires_confirmation_by_default is False
    assert delete.risk_level == ToolRiskLevel.IRREVERSIBLE
    assert delete.requires_confirmation_by_default is True
    assert delete.action_tags == ("delete",)
    assert ambiguous.risk_level == ToolRiskLevel.HIGH_RISK
    assert ambiguous.requires_confirmation_by_default is True
    assert registry.discovered_tool_names() == [
        "project_find_items",
        "project_delete_item",
        "project_process_item",
    ]


def test_discovered_tool_schema_generates_security_descriptor_metadata(tmp_path):
    registry = _load_registry(
        tmp_path,
        """
        [[servers]]
        id = "mail"
        prefix = "mail"
        enabled = true
        transport = "stdio"
        [servers.stdio]
        command = "python"
        """,
    )
    metadata = registry.register_discovered_tool(
        registry.servers[0],
        _discovered_tool(
            "send_email",
            "Send an email message to recipients.",
            input_schema={
                "type": "object",
                "required": ["to", "body"],
                "properties": {
                    "to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recipient email addresses.",
                    },
                    "subject": {"type": "string"},
                    "body": {
                        "type": "string",
                        "description": "Message body content.",
                    },
                },
            },
        ),
    )

    assert metadata.operation == "send"
    assert metadata.capabilities == ("email.send", "communication.send")
    assert metadata.argument_roles["destinations"] == ("to",)
    assert metadata.argument_roles["data"] == ("subject", "body")
    assert metadata.required_arguments == ("to", "body")
    assert metadata.metadata_confidence >= 0.7
    assert "input_schema" in metadata.metadata_provenance


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            """
            [[servers]]
            id = "one"
            prefix = "same"
            enabled = false
            transport = "stdio"
            [servers.stdio]
            command = "python"

            [[servers]]
            id = "two"
            prefix = "same"
            enabled = false
            transport = "stdio"
            [servers.stdio]
            command = "python"
            """,
            "prefixes must be unique",
        ),
        (
            """
            [[servers]]
            id = "one"
            prefix = "one"
            enabled = false
            transport = "websocket"
            """,
            "transport must be",
        ),
        (
            """
            [[servers]]
            id = "one"
            prefix = "one"
            enabled = false
            transport = "stdio"
            risk_level = "safe"
            [servers.stdio]
            command = "python"
            """,
            "unsupported field",
        ),
        (
            """
            [[servers]]
            id = "one"
            prefix = "one"
            enabled = false
            transport = "stdio"
            [servers.stdio]
            command = "${MISSING_MCP_COMMAND}"
            """,
            "missing environment variable",
        ),
    ],
)
def test_registry_rejects_invalid_configuration(tmp_path, body, message):
    with pytest.raises(McpRegistryError, match=message):
        _load_registry(tmp_path, body)


def test_unknown_dynamic_mcp_tool_is_traced_and_requires_approval(tmp_path):
    registry = _load_registry(
        tmp_path,
        """
        [[servers]]
        id = "example"
        prefix = "example"
        enabled = true
        transport = "stdio"
        [servers.stdio]
        command = "python"
        """,
    )
    session = GoogleADKTraceSession(
        session_id="dynamic_mcp",
        agent_id="terminal_assistant",
        available_tools=["run_shell_command"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="mcp_test",
        metadata_resolver=registry.metadata_for,
    )
    session.start_turn("Use the example integration.")

    result = session.record_tool_call("example_new_tool", {"value": "x"}, call_id="dynamic")

    tool = result.trace.proposed_tool_call
    assert tool.tool_name in session.available_tools
    assert tool.mcp_server == "example"
    assert tool.risk_level == "high_risk"
    assert tool.tool_name in result.trace.intent.confirmation_required_tools
    assert result.decision.decision in {"require_approval", "block"}


def test_action_tags_make_negative_intent_generic(tmp_path):
    registry = _load_registry(
        tmp_path,
        """
        [[servers]]
        id = "project"
        prefix = "project"
        enabled = true
        transport = "stdio"
        [servers.stdio]
        command = "python"
        """,
    )
    session = GoogleADKTraceSession(
        session_id="negative_action",
        agent_id="terminal_assistant",
        available_tools=["project_publish"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="mcp_test",
        metadata_resolver=registry.metadata_for,
    )
    session.start_turn("Prepare the release but do not publish it.")

    result = session.record_tool_call("project_publish", {}, call_id="publish")

    assert result.trace.intent.intent_forbidden_tools == ["project_publish"]
    assert result.decision.decision == "require_approval"


def test_irreversible_action_tag_must_be_explicitly_requested(tmp_path):
    registry = _load_registry(
        tmp_path,
        """
        [[servers]]
        id = "messages"
        prefix = "messages"
        enabled = true
        transport = "stdio"
        [servers.stdio]
        command = "python"
        """,
    )
    session = GoogleADKTraceSession(
        session_id="implicit_action",
        agent_id="terminal_assistant",
        available_tools=["messages_send"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="mcp_test",
        metadata_resolver=registry.metadata_for,
    )
    session.start_turn("Draft a message for Maya.")

    result = session.record_tool_call("messages_send", {}, call_id="send")

    assert result.trace.intent.intent_forbidden_tools == ["messages_send"]
    assert result.decision.decision == "require_approval"


def _load_registry(tmp_path, body: str) -> McpRegistry:
    path = tmp_path / "mcp.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return McpRegistry.load(path)


def _discovered_tool(
    name: str,
    description: str,
    *,
    read_only: bool | None = None,
    destructive: bool | None = None,
    input_schema: dict | None = None,
):
    annotations = SimpleNamespace(
        readOnlyHint=read_only,
        destructiveHint=destructive,
    )
    return SimpleNamespace(
        name=name,
        description=description,
        annotations=annotations,
        inputSchema=input_schema or {},
    )
