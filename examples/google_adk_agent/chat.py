"""Standalone interactive chat loop for the terminal-assistant ADK agent.

This is an alternative to ``adk run`` / ``adk web`` that needs no extra CLI: it
wires the agent into an ADK Runner with an in-memory session and reads turns from
stdin. Run it from the repo root:

    uv run examples/google_adk_agent/chat.py

Type your message and press Enter. Use "exit" or Ctrl-D to quit.
Requires ``google-adk`` and a Gemini API key (``GOOGLE_API_KEY``).
"""

from __future__ import annotations

import asyncio
import os
import sys

# Allow direct script execution by ensuring the repository is importable.
_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AGENT_DIR))
_REPO_ROOT = os.path.dirname(os.path.dirname(_AGENT_DIR))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

# Load the repo root .env so GOOGLE_API_KEY etc. are available even when this
# script is run directly.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ModuleNotFoundError:
    pass

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
except ModuleNotFoundError:  # pragma: no cover - guidance for first-time setup
    sys.exit(
        "google-adk is not installed. Install it with:\n"
        "    uv sync   (or: pip install google-adk)\n"
        "and set a Gemini API key, e.g. export GOOGLE_API_KEY=..."
    )

from examples.google_adk_agent.agent import MCP_SERVER_STATUSES, root_agent  # noqa: E402
APP_NAME = "adk_terminal_assistant"
USER_ID = "local_user"
SESSION_ID = "local_session"
TRACE_NAMESPACE = os.environ.get("AGENTGUARD_ADK_TRACE_NAMESPACE", "google_adk")
TRACE_ROOT = os.environ.get("AGENTGUARD_TRACE_ROOT", os.path.join(_REPO_ROOT, "data", "traces"))


def _render_event(event) -> None:
    """Print tool calls/results and the agent's final text reply."""
    content = getattr(event, "content", None)
    if content and content.parts:
        for part in content.parts:
            call = getattr(part, "function_call", None)
            if call:
                print(f"  → tool: {call.name}({dict(call.args or {})})")
            response = getattr(part, "function_response", None)
            if response:
                print("  ← tool returned")

    if event.is_final_response() and content and content.parts:
        text = "".join(part.text or "" for part in content.parts)
        if text:
            print(f"\nagent: {text}\n")


async def main() -> None:
    if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")):
        print(
            "Warning: no GOOGLE_API_KEY found in the environment or repo root .env. "
            "The agent will fail to call the model until you set one.\n",
            file=sys.stderr,
        )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    trace_path = os.path.join(TRACE_ROOT, "v1", TRACE_NAMESPACE, "traces.jsonl")

    print(f"Chatting with '{root_agent.name}' (model: {root_agent.model}).")
    if MCP_SERVER_STATUSES:
        for status in MCP_SERVER_STATUSES:
            state = "ready" if status.ready else status.detail
            print(f"MCP server '{status.id}' ({status.transport}, prefix {status.prefix}_): {state}.")
    else:
        print("No MCP servers configured.")
    print(f"Writing AgentGuard v1 traces to {trace_path}.")
    print("Type a message, or 'exit' to quit.\n")

    while True:
        try:
            user_input = input("you: ").strip()
        except EOFError:
            print()
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        message = types.Content(role="user", parts=[types.Part(text=user_input)])
        async for event in runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=message
        ):
            _render_event(event)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
