"""Create the real OpenClaw productivity trace agent workspace."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from _bootstrap import bootstrap


AGENT_ID = "agentguard_productivity"
DEFAULT_WORKSPACE = ".openclaw-traces/productivity_workspace"
TEMPLATE_DIR = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "openclaw_trace_agents"
    / "configs"
    / "productivity_agent"
    / "workspace_template"
)


def main() -> None:
    bootstrap()
    repo_root = Path(__file__).resolve().parents[1]
    profile = os.environ.get("OPENCLAW_TRACE_PROFILE", "agentguard-traces")
    model = os.environ.get("OPENCLAW_TRACE_MODEL", "google/gemini-2.5-pro")
    workspace = repo_root / os.environ.get("OPENCLAW_TRACE_PRODUCTIVITY_WORKSPACE", DEFAULT_WORKSPACE)

    shutil.copytree(TEMPLATE_DIR, workspace, dirs_exist_ok=True)
    tool_path = workspace / "tools" / "productivity_tool.py"
    tool_path.chmod(0o755)

    if _agent_exists(profile):
        print(f"OpenClaw agent already exists: {AGENT_ID}")
        print(f"Updated workspace template at: {workspace}")
        return

    command = [
        "openclaw",
        "--profile",
        profile,
        "agents",
        "add",
        AGENT_ID,
        "--workspace",
        str(workspace),
        "--model",
        model,
        "--non-interactive",
        "--json",
    ]
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to create OpenClaw productivity agent. "
            f"returncode={completed.returncode}; stderr={completed.stderr.strip()}"
        )
    print(completed.stdout.strip())
    print(f"Created OpenClaw agent: {AGENT_ID}")
    print(f"Workspace: {workspace}")


def _agent_exists(profile: str) -> bool:
    completed = subprocess.run(
        ["openclaw", "--profile", profile, "agents", "list", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return False
    try:
        agents = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False
    return any(agent.get("id") == AGENT_ID for agent in agents)


if __name__ == "__main__":
    main()
