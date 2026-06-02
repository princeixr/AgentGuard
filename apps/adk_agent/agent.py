"""A conversational Google ADK agent with a terminal-command tool.

This is a self-contained demo agent you can chat with. It exposes a single tool,
``run_shell_command``, that executes commands on the local machine and returns
their output, so the model can inspect the filesystem, run scripts, check tool
versions, etc.

Run it with the ADK CLI from the repo root:

    adk run apps/adk_agent        # interactive terminal chat
    adk web                       # browser UI; pick "adk_agent"

or with the bundled standalone chat loop:

    python apps/adk_agent/chat.py

Requires ``google-adk`` (``pip install google-adk``) and a Gemini API key in the
environment (``GOOGLE_API_KEY``). ADK auto-loads ``apps/adk_agent/.env``.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from google.adk.agents import Agent

from agentguard.runtime.google_adk_adapter import GoogleADKTraceSession

# How long a single command may run before we give up on it.
COMMAND_TIMEOUT_SECONDS = int(os.environ.get("ADK_COMMAND_TIMEOUT_SECONDS", "60"))

# Cap returned output so a chatty command can't blow up the model context.
MAX_OUTPUT_CHARS = int(os.environ.get("ADK_MAX_OUTPUT_CHARS", "20000"))
TRACE_NAMESPACE = os.environ.get("AGENTGUARD_ADK_TRACE_NAMESPACE", "google_adk")
TRACE_ROOT = os.environ.get("AGENTGUARD_TRACE_ROOT", "data/traces")
AGENT_ID = "terminal_assistant"
APP_NAME = "adk_terminal_assistant"
AVAILABLE_TOOLS = ["run_shell_command"]

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


def _before_tool_callback(tool, args: dict[str, Any], tool_context) -> None:
    tracer = _get_trace_session(tool_context)
    tracer.start_turn(_extract_user_text(tool_context))
    tracer.record_tool_call(
        _tool_name(tool),
        args,
        call_id=getattr(tool_context, "function_call_id", None),
    )
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


root_agent = Agent(
    name=AGENT_ID,
    model=os.environ.get("ADK_MODEL", "gemini-3-flash-preview"),
    description="A conversational assistant that can run terminal commands on the local machine.",
    instruction=(
        "You are a helpful command-line assistant. Chat naturally with the user. "
        "When a request needs information from, or an action on, the local machine, "
        "call the run_shell_command tool with a single non-interactive shell command. "
        "Inspect the returned exit_code, stdout, and stderr, then explain the result "
        "in plain language. If a command fails, read stderr and either fix and retry "
        "or tell the user what went wrong."
    ),
    tools=[run_shell_command],
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
    on_tool_error_callback=_on_tool_error_callback,
)
