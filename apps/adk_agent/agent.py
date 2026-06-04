"""A conversational Google ADK agent with a terminal-command tool.

This is a self-contained demo agent you can chat with. It exposes a terminal
tool and, optionally, a Docker-backed Gmail MCP toolset.

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
from typing import Any

from google.adk.agents import Agent

from agentguard.runtime.google_adk_adapter import GoogleADKTraceSession, adk_runtime_policy

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
TRACE_ROOT = os.environ.get("AGENTGUARD_TRACE_ROOT", str(_REPO_ROOT / "data" / "traces"))
AGENT_ID = "terminal_assistant"
APP_NAME = "adk_terminal_assistant"
GMAIL_MCP_ENABLED = os.environ.get("ADK_GMAIL_MCP_ENABLED", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
GMAIL_MCP_DOCKER_IMAGE = os.environ.get(
    "GMAIL_MCP_DOCKER_IMAGE", "agentguard-gmail-mcp:artymclabin"
)
GMAIL_MCP_CREDENTIALS_VOLUME = os.environ.get("GMAIL_MCP_CREDENTIALS_VOLUME", "mcp-gmail")
GMAIL_MCP_TOOL_PREFIX = os.environ.get("GMAIL_MCP_TOOL_PREFIX", "gmail").strip("_") or "gmail"
GMAIL_MCP_RAW_TOOLS = [
    "search_emails",
    "read_email",
    "draft_email",
    "send_email",
    "send_draft",
]
GMAIL_MCP_TOOLS = [f"{GMAIL_MCP_TOOL_PREFIX}_{name}" for name in GMAIL_MCP_RAW_TOOLS]
AVAILABLE_TOOLS = ["run_shell_command"] + (GMAIL_MCP_TOOLS if GMAIL_MCP_ENABLED else [])
ENFORCE_APPROVAL = os.environ.get("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true").lower() in {
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


def _build_gmail_mcp_toolset() -> list[Any]:
    if not GMAIL_MCP_ENABLED:
        return []

    try:
        from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
        from mcp import StdioServerParameters
    except ImportError as exc:  # pragma: no cover - startup guidance
        raise RuntimeError(
            "Gmail MCP is enabled, but MCP dependencies are not installed. "
            "Run `uv sync` from the repo root and try again."
        ) from exc

    return [
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="docker",
                    args=[
                        "run",
                        "-i",
                        "--rm",
                        "-v",
                        f"{GMAIL_MCP_CREDENTIALS_VOLUME}:/gmail-server",
                        "-e",
                        "GMAIL_OAUTH_PATH=/gmail-server/gcp-oauth.keys.json",
                        "-e",
                        "GMAIL_CREDENTIALS_PATH=/gmail-server/credentials.json",
                        GMAIL_MCP_DOCKER_IMAGE,
                    ],
                ),
            ),
            tool_filter=GMAIL_MCP_RAW_TOOLS,
            tool_name_prefix=GMAIL_MCP_TOOL_PREFIX,
        )
    ]


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

    if runtime_policy == "require_approval" and ENFORCE_APPROVAL:
        approval_response = {
            "error": (
                "AgentGuard requires approval for this tool call. Approval UI is not "
                "implemented yet, so the tool was not executed."
            ),
            "approval_required": True,
            "blocked_by_agentguard": True,
            "tool_name": tool_name,
            "runtime_policy": runtime_policy,
            "firewall_decision": result.decision.decision,
            "guard_explanation": result.decision.explanation,
            "trace_id": result.trace.trace_id,
        }
        tracer.record_tool_response(tool_name, approval_response, call_id=call_id)
        return approval_response

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
        {"error": str(error), "args": args},
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
            available_tools=AVAILABLE_TOOLS,
            namespace=TRACE_NAMESPACE,
            trace_root=TRACE_ROOT,
            enable_elastic=ENABLE_ELASTIC,
            fail_on_elastic_error=FAIL_ON_ELASTIC_ERROR,
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


TOOLS = [run_shell_command] + _build_gmail_mcp_toolset()

root_agent = Agent(
    name=AGENT_ID,
    model=os.environ.get("ADK_MODEL", "gemini-3-flash-preview"),
    description=(
        "A conversational assistant that can run terminal commands and, when enabled, "
        "use a guarded Gmail MCP server."
    ),
    instruction=(
        "You are a helpful command-line assistant. Chat naturally with the user. "
        "When a request needs information from, or an action on, the local machine, "
        "call the run_shell_command tool with a single non-interactive shell command. "
        "When Gmail MCP tools are available, use Gmail search/read tools for inbox "
        "questions and Gmail draft tools when the user asks to prepare email. Only "
        "use Gmail send tools when the current user message explicitly asks you to "
        "send an email or send a draft. Never use run_shell_command, command-line "
        "mail clients, SMTP scripts, curl, or other shell fallbacks to send email. "
        "Inspect the returned exit_code, stdout, and stderr, then explain the result "
        "in plain language. If a command fails, read stderr and either fix and retry "
        "or tell the user what went wrong."
    ),
    tools=TOOLS,
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
    on_tool_error_callback=_on_tool_error_callback,
)
