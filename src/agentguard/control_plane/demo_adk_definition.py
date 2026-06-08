"""Product-facing definition of the Google ADK demo agent."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from agentguard.control_plane.registry import DEMO_AGENT_ID
from agentguard.runtime.google_adk_adapter import infer_adk_tool_metadata
from agentguard.runtime.mcp_registry import McpRegistry

DEMO_ADK_APP_NAME = "adk_terminal_assistant"
DEMO_ADK_RUNTIME_NAME = "terminal_assistant"
DEMO_ADK_DESCRIPTION = (
    "A conversational assistant that can run terminal commands and use guarded "
    "MCP servers configured declaratively."
)
BASE_ADK_INSTRUCTION = (
    "You are a helpful command-line assistant. Chat naturally with the user. "
    "When a request needs information from, or an action on, the local machine, "
    "call the run_shell_command tool with a single non-interactive shell command. "
    "Inspect the returned exit_code, stdout, and stderr, then explain the result "
    "in plain language. If a command fails, read stderr and either fix and retry "
    "or tell the user what went wrong."
)
_REPO_ROOT = Path(__file__).resolve().parents[3]


def mcp_config_path() -> Path:
    configured = Path(
        os.environ.get("ADK_MCP_CONFIG_PATH", str(_REPO_ROOT / "config" / "adk_mcp_servers.toml"))
    )
    return configured if configured.is_absolute() else _REPO_ROOT / configured


@lru_cache(maxsize=1)
def mcp_registry() -> McpRegistry:
    return McpRegistry.load(mcp_config_path())


def enabled_tools() -> list[str]:
    return ["run_shell_command", *mcp_registry().discovered_tool_names(ready_only=True)]


def agent_instruction() -> str:
    ready_servers = mcp_registry().ready_servers()
    if not ready_servers:
        return (
            f"{BASE_ADK_INSTRUCTION} No MCP servers are available in this runtime. "
            "Do not invent MCP tools. Explain that an MCP server must be enabled in "
            "config/adk_mcp_servers.toml when external integrations are requested."
        )
    server_names = ", ".join(f"{server.id} ({server.prefix}_*)" for server in ready_servers)
    return (
        f"{BASE_ADK_INSTRUCTION} The available MCP servers are: {server_names}. "
        "Use their prefixed tools for matching external integrations. Never invent a "
        "tool name, and never use run_shell_command as a fallback for an external "
        "integration action."
    )


def tool_registry() -> list[dict[str, Any]]:
    registry = mcp_registry()
    tools = [_tool_definition("run_shell_command", infer_adk_tool_metadata("run_shell_command"), True)]
    ready_ids = {server.id for server in registry.ready_servers()}
    for name in registry.discovered_tool_names():
        metadata = registry.metadata_for(name)
        if metadata is not None:
            tools.append(_tool_definition(name, metadata, metadata.mcp_server in ready_ids))
    return tools


def agent_definition() -> dict[str, Any]:
    registry = mcp_registry()
    return {
        "agent_id": DEMO_AGENT_ID,
        "runtime_name": DEMO_ADK_RUNTIME_NAME,
        "app_name": DEMO_ADK_APP_NAME,
        "framework": "google_adk",
        "model": os.environ.get("ADK_MODEL", "gemini-3-flash-preview"),
        "description": DEMO_ADK_DESCRIPTION,
        "system_instruction": agent_instruction(),
        "tools": tool_registry(),
        "callbacks": [
            "before_tool_callback: AgentGuard intercept and decision",
            "after_tool_callback: execution result and trace completion",
            "on_tool_error_callback: failed execution capture",
        ],
        "guardrails": {
            "policy_id": "pol_strict_intent_v1",
            "implementation": (
                "Functional deterministic policy plus weighted heuristic scorer v0.1; "
                "not a trained production anomaly model."
            ),
            "approval_enforced": os.environ.get(
                "AGENTGUARD_ADK_ENFORCE_APPROVAL", "true"
            ).lower()
            in {"1", "true", "yes", "on"},
            "trace_namespace": os.environ.get(
                "AGENTGUARD_ADK_TRACE_NAMESPACE", "google_adk"
            ),
        },
        "runtime": {
            "model_credentials_configured": bool(
                os.environ.get("GOOGLE_API_KEY")
                or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
            ),
            "mcp_config_path": str(mcp_config_path()),
            "mcp_servers": [status.as_dict() for status in registry.statuses()],
        },
        "test_scenarios": [
            {
                "id": "inspect_workspace",
                "name": "Inspect workspace",
                "prompt": "Show me the current directory and list the top-level files.",
                "expected_behavior": "Uses the guarded shell tool for read-only inspection.",
            }
        ],
    }


def _tool_definition(name: str, metadata, enabled: bool) -> dict[str, Any]:
    return {
        "name": name,
        "description": metadata.description or f"Google ADK tool: {name}",
        "category": metadata.category,
        "risk_level": (
            metadata.risk_level.value
            if hasattr(metadata.risk_level, "value")
            else str(metadata.risk_level)
        ),
        "side_effect_type": metadata.side_effect_type,
        "requires_confirmation": metadata.requires_confirmation_by_default,
        "irreversible": metadata.irreversible,
        "enabled": enabled,
        "provider": metadata.provider or "local",
    }
