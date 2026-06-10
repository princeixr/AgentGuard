from types import SimpleNamespace
from pathlib import Path

from apps.adk_agent import agent as adk_agent
from agentguard.runtime.google_adk_adapter import GoogleADKTraceSession
from agentguard.tracing.serializers import load_jsonl


def test_adk_agent_default_trace_root_points_to_repo_data_dir():
    assert Path(adk_agent.TRACE_ROOT).is_absolute()


def test_google_adk_trace_session_writes_canonical_trace_and_live_events(tmp_path):
    tracer = GoogleADKTraceSession(
        session_id="session_adk_001",
        agent_id="terminal_assistant",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        available_tools=["run_shell_command"],
        trace_root=tmp_path / "traces",
    )

    tracer.start_turn("List this directory.")
    trace = tracer.record_tool_call(
        "run_shell_command",
        {"command": "ls"},
        call_id="call_adk_001",
    )
    tracer.record_tool_response(
        "run_shell_command",
        {"command": "ls", "exit_code": 0, "stdout": "README.md\n", "stderr": "", "timed_out": False},
        call_id="call_adk_001",
    )

    records = load_jsonl(tmp_path / "traces" / "v1" / "google_adk" / "traces.jsonl")
    live_events = load_jsonl(tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl")

    assert len(records) == 1
    assert records[0]["schema_version"] == "agentguard.trace.v1"
    assert records[0]["trace_id"] == trace.trace.trace_id
    assert records[0]["source"]["agent_framework"] == "google_adk"
    assert records[0]["source"]["source_type"] == "live_google_adk"
    assert records[0]["intent"]["raw_user_request"] == "List this directory."
    assert records[0]["intent"]["domain"] == "shell"
    assert records[0]["proposed_tool_call"]["tool_name"] == "run_shell_command"
    assert records[0]["proposed_tool_call"]["tool_category"] == "shell"
    assert records[0]["proposed_tool_call"]["risk_level"] == "low_side_effect"
    assert records[0]["proposed_tool_call"]["side_effect_type"] == "shell_command"
    assert records[0]["execution"]["status"] == "proposed"
    assert [event["event_type"] for event in live_events] == [
        "tool_proposed",
        "guard_scored",
        "guard_decided",
        "tool_executed",
    ]


def test_google_adk_trace_session_tracks_prior_tool_trajectory(tmp_path):
    tracer = GoogleADKTraceSession(
        session_id="session_adk_001",
        agent_id="terminal_assistant",
        available_tools=["run_shell_command"],
        trace_root=tmp_path / "traces",
    )

    tracer.start_turn("Show Python and then list files.")
    first = tracer.record_tool_call(
        "run_shell_command",
        {"command": "python3 --version"},
        call_id="call_001",
    )
    tracer.record_tool_response(
        "run_shell_command",
        {"exit_code": 0, "stdout": "Python 3.12.0\n", "stderr": "", "timed_out": False},
        call_id="call_001",
    )
    second = tracer.record_tool_call(
        "run_shell_command",
        {"command": "ls"},
        call_id="call_002",
    )

    assert second.trace.previous_trace_id == first.trace.trace_id
    assert second.trace.step_index == 2
    assert second.trace.trajectory.prior_tool_names == ["run_shell_command"]
    assert second.trace.trajectory.previous_output_summary == "exit_code=0; stdout=Python 3.12.0"


def test_adk_tool_callbacks_accept_adk_keyword_arguments(tmp_path, monkeypatch):
    monkeypatch.setattr(adk_agent, "TRACE_ROOT", str(tmp_path / "traces"))
    monkeypatch.setattr(adk_agent, "_TRACE_SESSIONS", {})
    tool_context = SimpleNamespace(
        function_call_id="call_adk_001",
        session=SimpleNamespace(id="session_adk_001"),
        agent_name="terminal_assistant",
        user_content=SimpleNamespace(
            parts=[SimpleNamespace(text="Is there a folder named hola in my home directory?")]
        ),
    )
    tool = SimpleNamespace(name="run_shell_command")

    adk_agent._before_tool_callback(
        tool=tool,
        args={"command": "ls -d ~/hola"},
        tool_context=tool_context,
    )
    adk_agent._after_tool_callback(
        tool=tool,
        args={"command": "ls -d ~/hola"},
        tool_context=tool_context,
        tool_response={"exit_code": 1, "stdout": "", "stderr": "No such file", "timed_out": False},
    )

    records = load_jsonl(tmp_path / "traces" / "v1" / "google_adk" / "traces.jsonl")
    live_events = load_jsonl(tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl")

    assert records[0]["proposed_tool_call"]["arguments"] == {"command": "ls -d ~/hola"}
    assert records[0]["intent"]["raw_user_request"] == (
        "Is there a folder named hola in my home directory?"
    )
    assert [event["event_type"] for event in live_events] == [
        "tool_proposed",
        "guard_scored",
        "guard_decided",
        "tool_failed",
    ]


def test_adk_tool_callback_blocks_send_without_explicit_send(tmp_path, monkeypatch):
    monkeypatch.setattr(adk_agent, "TRACE_ROOT", str(tmp_path / "traces"))
    monkeypatch.setattr(adk_agent, "AVAILABLE_TOOLS", ["workspace_gmail_createDraft", "workspace_gmail_send"])
    monkeypatch.setattr(adk_agent, "_TRACE_SESSIONS", {})
    tool_context = SimpleNamespace(
        function_call_id="call_gmail_001",
        session=SimpleNamespace(id="session_adk_001"),
        agent_name="terminal_assistant",
        user_content=SimpleNamespace(parts=[SimpleNamespace(text="Draft an email to Maya.")]),
    )
    tool = SimpleNamespace(name="workspace_gmail_send")

    response = adk_agent._before_tool_callback(
        tool=tool,
        args={"to": ["maya@example.com"], "subject": "Hi", "body": "Hello"},
        tool_context=tool_context,
    )

    records = load_jsonl(tmp_path / "traces" / "v1" / "google_adk" / "traces.jsonl")
    live_events = load_jsonl(tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl")

    assert response["blocked_by_agentguard"] is True
    assert records[0]["proposed_tool_call"]["tool_name"] == "workspace_gmail_send"
    assert records[0]["proposed_tool_call"]["mcp_server"] == "workspace"
    assert records[0]["proposed_tool_call"]["risk_level"] == "external_write"
    assert records[0]["proposed_tool_call"]["side_effect_type"] == "external_send"
    assert [event["event_type"] for event in live_events][:4] == [
        "tool_proposed",
        "guard_scored",
        "guard_decided",
        "tool_blocked",
    ]


def test_adk_tool_callback_requires_approval_for_explicit_send(tmp_path, monkeypatch):
    monkeypatch.setattr(adk_agent, "TRACE_ROOT", str(tmp_path / "traces"))
    monkeypatch.setattr(adk_agent, "AVAILABLE_TOOLS", ["workspace_gmail_createDraft", "workspace_gmail_send"])
    monkeypatch.setattr(adk_agent, "_TRACE_SESSIONS", {})
    tool_context = SimpleNamespace(
        function_call_id="call_gmail_001",
        session=SimpleNamespace(id="session_adk_001"),
        agent_name="terminal_assistant",
        user_content=SimpleNamespace(
            parts=[SimpleNamespace(text="Send an email to Maya with the final update.")]
        ),
    )
    tool = SimpleNamespace(name="workspace_gmail_send")

    response = adk_agent._before_tool_callback(
        tool=tool,
        args={"to": ["maya@example.com"], "subject": "Update", "body": "Done"},
        tool_context=tool_context,
    )

    assert response["blocked_by_agentguard"] is True
    assert response["approval_required"] is True
    assert response["runtime_policy"] == "require_approval"


def test_adk_tool_callback_uses_local_tool_metadata_without_provider_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(adk_agent, "TRACE_ROOT", str(tmp_path / "traces"))
    monkeypatch.setattr(adk_agent, "_TRACE_SESSIONS", {})
    tool_context = SimpleNamespace(
        function_call_id="call_shell_email_001",
        session=SimpleNamespace(id="session_adk_001"),
        agent_name="terminal_assistant",
        user_content=SimpleNamespace(
            parts=[SimpleNamespace(text="Send an email to Maya with the final update.")]
        ),
    )
    tool = SimpleNamespace(name="run_shell_command")

    response = adk_agent._before_tool_callback(
        tool=tool,
        args={"command": "printf 'Done' | mail -s Update maya@example.com"},
        tool_context=tool_context,
    )

    assert response is None


def test_workspace_mcp_tools_have_conservative_metadata():
    send = adk_agent.MCP_REGISTRY.metadata_for("workspace_gmail_send")
    search = adk_agent.MCP_REGISTRY.metadata_for("workspace_gmail_search")

    assert send is not None
    assert search is not None
    assert send.risk_level == "external_write"
    assert send.side_effect_type == "external_send"
    assert send.mcp_server == "workspace"
    assert search.risk_level == "read_only"
