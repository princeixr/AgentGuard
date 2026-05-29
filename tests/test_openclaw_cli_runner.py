from pathlib import Path

from apps.openclaw_trace_agents.cli_runner import OpenClawCliRunner


def test_openclaw_cli_runner_builds_expected_command():
    runner = OpenClawCliRunner(profile="agentguard", output_root=Path("/tmp/openclaw-runs"))

    command = runner._build_command(
        agent_name="email",
        session_id="session_001",
        message="Summarize the inbox.",
    )

    assert command[:4] == ["openclaw", "--profile", "agentguard", "agent"]
    assert "--local" in command
    assert command[command.index("--agent") + 1] == "email"
    assert command[command.index("--session-id") + 1] == "session_001"
    assert command[command.index("--message") + 1] == "Summarize the inbox."
