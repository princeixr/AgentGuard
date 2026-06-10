"""Independent Google ADK personal agent."""

from __future__ import annotations

import hashlib
import subprocess

from agentguard_sdk import AgentRegistration, ToolManifest
from google.adk.agents import Agent

from personal_agent.guard import AgentGuardAdkInterceptor, build_guard_client
from personal_agent.mcp.config import load_servers
from personal_agent.mcp.registry import McpRegistry
from personal_agent.mcp.toolsets import build_mcp_toolsets
from personal_agent.settings import settings

DESCRIPTION = "Personal productivity assistant with terminal and MCP tools."
INSTRUCTION = (
    "You are a personal productivity assistant. Use only registered tools. "
    "Explain tool results clearly and never invent a tool name."
)

registry = McpRegistry(load_servers(settings.mcp_config_path))
guard_client = build_guard_client()
interceptor = AgentGuardAdkInterceptor(guard_client)


def run_shell_command(command: str) -> dict:
    """Execute one non-interactive shell command."""
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=settings.command_timeout_seconds,
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[: settings.max_output_chars],
        "stderr": completed.stderr[: settings.max_output_chars],
    }


def build_registration() -> AgentRegistration:
    instruction_hash = hashlib.sha256(INSTRUCTION.encode("utf-8")).hexdigest()
    shell_manifest = ToolManifest(
        name="run_shell_command",
        source_name="run_shell_command",
        provider="local_terminal",
        framework="google_adk",
        transport="native",
        description=run_shell_command.__doc__ or "Execute one shell command.",
        input_schema={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
        metadata_provenance=["agent_function_schema"],
    )
    return AgentRegistration(
        workspace_id=settings.workspace_id,
        agent_id=settings.agent_id,
        deployment_id=settings.deployment_id,
        integration_id=settings.integration_id,
        name="Google ADK Personal Agent",
        description=DESCRIPTION,
        framework="google_adk",
        runtime_version="development",
        environment=settings.environment,
        system_instruction_hash=f"sha256:{instruction_hash}",
        system_instruction_summary=INSTRUCTION,
        manifest_version="development",
        tools=[shell_manifest, *registry.manifests()],
        agent_ui_url=settings.agent_ui_url,
    )


root_agent = Agent(
    name=settings.agent_id,
    model=settings.model,
    description=DESCRIPTION,
    instruction=INSTRUCTION,
    tools=[run_shell_command, *build_mcp_toolsets(registry)],
    before_tool_callback=interceptor.before_tool,
    after_tool_callback=interceptor.after_tool,
    on_tool_error_callback=interceptor.on_tool_error,
)

guard_client.register(build_registration())
