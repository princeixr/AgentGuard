"""A conversational Google ADK agent with a terminal-command tool.

This is a self-contained demo agent you can chat with. It exposes a terminal
tool and any MCP servers enabled in ``config/adk_mcp_servers.toml``.

Run it with the ADK CLI from the repo root:

    adk run apps/adk_agent        # interactive terminal chat
    adk web                       # browser UI; pick "adk_agent"

or with the bundled standalone chat loop:

    python apps/adk_agent/chat.py

Requires ``google-adk`` (``pip install google-adk``) and configuration in the
repo root ``.env``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, cast

from google.adk.agents import Agent

from agentguard.control_plane.demo_adk_definition import (
    DEMO_ADK_APP_NAME,
    DEMO_ADK_DESCRIPTION,
    agent_instruction,
    enabled_tools,
    mcp_registry,
)
from agentguard.control_plane.registry import DEMO_AGENT_ID, DemoAgentRegistry
from agentguard.firewall_v2.models import FirewallMode
from agentguard.runtime.google_adk_adapter import GoogleADKTraceSession, adk_runtime_policy
from agentguard.runtime.mcp_registry import McpRegistry

_REPO_ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ModuleNotFoundError:
    pass

# How long a single command may run before we give up on it.
COMMAND_TIMEOUT_SECONDS = int(os.environ.get("ADK_COMMAND_TIMEOUT_SECONDS", "60"))

# Cap returned output so a chatty command can't blow up the model context.
MAX_OUTPUT_CHARS = int(os.environ.get("ADK_MAX_OUTPUT_CHARS", "20000"))
TRACE_NAMESPACE = os.environ.get("AGENTGUARD_ADK_TRACE_NAMESPACE", "google_adk")
TRACE_ROOT = Path(
    os.environ.get("AGENTGUARD_TRACE_ROOT", str(_REPO_ROOT / "data" / "traces"))
)
if not TRACE_ROOT.is_absolute():
    TRACE_ROOT = _REPO_ROOT / TRACE_ROOT
AGENT_ID = DEMO_AGENT_ID
APP_NAME = DEMO_ADK_APP_NAME
RUNTIME_IDENTITY = DemoAgentRegistry().runtime_identity(AGENT_ID)
MCP_REGISTRY = mcp_registry()
MCP_SERVER_STATUSES = MCP_REGISTRY.statuses()
AVAILABLE_TOOLS = enabled_tools()
ENFORCE_APPROVAL = os.environ.get("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
FORCE_BLOCK = os.environ.get(
    "AGENTGUARD_FORCE_BLOCK",
    os.environ.get("FORCE_BLOCK", "false"),
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ENABLE_ELASTIC = os.environ.get("AGENTGUARD_ADK_ELASTIC_ENABLED")
if ENABLE_ELASTIC is not None:
    ENABLE_ELASTIC = ENABLE_ELASTIC.strip().lower() in {"1", "true", "yes", "on"}
FAIL_ON_ELASTIC_ERROR = os.environ.get(
    "AGENTGUARD_ADK_FAIL_ON_ELASTIC_ERROR", "false"
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MOCK_PIPELINE_ONLY = os.environ.get(
    "AGENTGUARD_MOCK_PIPELINE_ONLY",
    os.environ.get("AGENTGUARD_MOCK_RUN", "false"),
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_firewall_mode = os.environ.get("AGENTGUARD_FIREWALL_MODE", "v1").lower()
FIREWALL_MODE: FirewallMode = (
    cast(FirewallMode, _firewall_mode)
    if _firewall_mode in {"v1", "v2_shadow", "v2"}
    else "v1"
)

_TRACE_SESSIONS: dict[str, GoogleADKTraceSession] = {}


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + f"\n...[truncated, {len(text) - MAX_OUTPUT_CHARS} more chars]"


def run_shell_command(command: str) -> dict:
    """Run a shell command on the local machine and return its output.

    Use this to inspect the filesystem, run scripts, check installed tool
    versions, read files, or perform any task that is easiest from a terminal.
    Prefer non-interactive commands; this tool cannot answer interactive prompts.

    Args:
        command: The shell command to execute, e.g. "ls -la" or "python --version".

    Returns:
        A dict with keys:
            command: the command that was run.
            exit_code: the process exit code (0 means success), or null on timeout.
            stdout: captured standard output (truncated if very long).
            stderr: captured standard error (truncated if very long).
            timed_out: true if the command exceeded the timeout.
    """
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": _truncate(completed.stdout),
            "stderr": _truncate(completed.stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "stdout": _truncate(exc.stdout or "" if isinstance(exc.stdout, str) else ""),
            "stderr": _truncate(exc.stderr or "" if isinstance(exc.stderr, str) else ""),
            "timed_out": True,
        }


def _build_mcp_toolsets(registry: McpRegistry) -> list[Any]:
    try:
        from google.adk.tools.mcp_tool.mcp_session_manager import (
            StdioConnectionParams,
            StreamableHTTPConnectionParams,
        )
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
        from mcp import StdioServerParameters
    except ImportError as exc:  # pragma: no cover - startup guidance
        raise RuntimeError(
            "An MCP server is enabled, but MCP dependencies are not installed. "
            "Run `uv sync` from the repo root and try again."
        ) from exc

    class RegistryAwareMcpToolset(McpToolset):
        def __init__(self, *, registry, server, **kwargs):
            self._agentguard_registry = registry
            self._agentguard_server = server
            super().__init__(**kwargs)

        async def get_tools(self, readonly_context=None):
            tools = await super().get_tools(readonly_context)
            for tool in tools:
                self._agentguard_registry.register_discovered_tool(
                    self._agentguard_server, tool
                )
            return tools

    toolsets = []
    for server in registry.ready_servers():
        if server.transport == "stdio":
            connection_params = StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=server.stdio_command or "",
                    args=list(server.stdio_args),
                    env=server.stdio_env or None,
                )
            )
        else:
            connection_params = StreamableHTTPConnectionParams(
                url=server.http_url or "",
                headers=server.http_headers or None,
            )
        toolsets.append(
            RegistryAwareMcpToolset(
                registry=registry,
                server=server,
                connection_params=connection_params,
                tool_filter=None,
                tool_name_prefix=server.prefix,
            )
        )
    return toolsets


def _before_tool_callback(tool, args: dict[str, Any], tool_context):
    tracer = _get_trace_session(tool_context)
    user_text = _extract_user_text(tool_context)
    tool_name = _tool_name(tool)
    call_id = getattr(tool_context, "function_call_id", None)
    tracer.start_turn(user_text)
    result = tracer.record_tool_call(
        tool_name,
        args,
        call_id=call_id,
    )
    runtime_policy = adk_runtime_policy(result.decision.decision)

    should_stop = MOCK_PIPELINE_ONLY or runtime_policy == "block" or (
        runtime_policy == "require_approval" and ENFORCE_APPROVAL
    )
    if should_stop:
        is_approval = runtime_policy == "require_approval"
        blocked_response = {
            "error": (
                "AgentGuard mock pipeline mode is enabled. The full guard pipeline "
                "was evaluated and logged, but the tool was not executed."
                if MOCK_PIPELINE_ONLY
                else
                "AgentGuard requires approval for this tool call. Approval UI is not "
                "implemented yet, so the tool was not executed."
                if is_approval
                else "AgentGuard blocked this tool call. The tool was not executed."
            ),
            "approval_required": is_approval,
            "blocked_by_agentguard": True,
            "mock_pipeline_only": MOCK_PIPELINE_ONLY,
            "tool_name": tool_name,
            "runtime_policy": runtime_policy,
            "firewall_decision": result.decision.decision,
            "guard_explanation": result.decision.explanation,
            "trace_id": result.trace.trace_id,
        }
        tracer.record_tool_response(tool_name, blocked_response, call_id=call_id)
        return blocked_response

    return None


def _after_tool_callback(tool, args: dict[str, Any], tool_context, tool_response: dict) -> None:
    _get_trace_session(tool_context).record_tool_response(
        _tool_name(tool),
        tool_response,
        call_id=getattr(tool_context, "function_call_id", None),
    )
    return None


def _on_tool_error_callback(tool, args: dict[str, Any], tool_context, error: Exception) -> None:
    _get_trace_session(tool_context).record_tool_response(
        _tool_name(tool),
        {"error": MCP_REGISTRY.redact(str(error)), "args": args},
        call_id=getattr(tool_context, "function_call_id", None),
    )
    return None


def _get_trace_session(context) -> GoogleADKTraceSession:
    session_id = _session_id(context)
    if session_id not in _TRACE_SESSIONS:
        _TRACE_SESSIONS[session_id] = GoogleADKTraceSession(
            session_id=session_id,
            agent_id=AGENT_ID,
            runtime_agent_id=getattr(context, "agent_name", None) or AGENT_ID,
            agent_config_id=APP_NAME,
            runtime_identity=RUNTIME_IDENTITY,
            available_tools=AVAILABLE_TOOLS,
            namespace=TRACE_NAMESPACE,
            trace_root=TRACE_ROOT,
            enable_elastic=ENABLE_ELASTIC,
            fail_on_elastic_error=FAIL_ON_ELASTIC_ERROR,
            force_block=FORCE_BLOCK,
            tool_metadata={
                name: metadata
                for name in MCP_REGISTRY.discovered_tool_names()
                if (metadata := MCP_REGISTRY.metadata_for(name)) is not None
            },
            metadata_resolver=MCP_REGISTRY.metadata_for,
            firewall_mode=FIREWALL_MODE,
        )
    return _TRACE_SESSIONS[session_id]


def _session_id(context) -> str:
    session = getattr(context, "session", None)
    return (
        getattr(session, "id", None)
        or getattr(session, "session_id", None)
        or getattr(context, "invocation_id", None)
        or "local_session"
    )


def _extract_user_text(context) -> str:
    content = getattr(context, "user_content", None)
    parts = getattr(content, "parts", None) or []
    text = "".join(str(getattr(part, "text", "") or "") for part in parts).strip()
    return text or "User request unavailable from ADK context."


def _tool_name(tool) -> str:
    return getattr(tool, "name", None) or getattr(tool, "__name__", None) or str(tool)


TOOLS = [run_shell_command] + _build_mcp_toolsets(MCP_REGISTRY)

root_agent = Agent(
    name=AGENT_ID,
    model=os.environ.get("ADK_MODEL", "gemini-3-flash-preview"),
    description=DEMO_ADK_DESCRIPTION,
    instruction=agent_instruction(),
    tools=TOOLS,
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
    on_tool_error_callback=_on_tool_error_callback,
)
