from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from agentguard.control_plane.registry import (
    DEMO_AGENT_ID,
    DEMO_DEPLOYMENT_ID,
    DEMO_INTEGRATION_ID,
    DEMO_WORKSPACE_ID,
    DemoAgentRegistry,
)
from agentguard.runtime.google_adk_adapter import GoogleADKTraceSession, adk_runtime_policy
from agentguard.runtime.mcp_registry import McpRegistry
from agentguard.tracing.serializers import load_jsonl
from agentguard.tracing.trace_store import TraceStore


def test_google_adk_trace_session_runs_firewall_before_execution(tmp_path):
    session = GoogleADKTraceSession(
        session_id="adk_test_session",
        agent_id="terminal_assistant",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        available_tools=["run_shell_command", "gmail_send_email"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="google_adk_test",
        metadata_resolver=_mcp_registry().metadata_for,
    )
    session.start_turn("Draft a reply but do not send it.")

    result = session.record_tool_call(
        "gmail_send_email",
        {"to": "finance@example.com", "body": "Draft body"},
        call_id="call_001",
    )

    assert adk_runtime_policy(result.decision.decision) in {"require_approval", "block"}
    assert result.decision.decision in {"require_approval", "block"}
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "traces.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "features.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "scores.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "decisions.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "session_risk").exists()


def test_google_adk_trace_session_propagates_runtime_identity(tmp_path):
    session = GoogleADKTraceSession(
        session_id="adk_owned_session",
        agent_id="runtime_alias",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        runtime_identity=DemoAgentRegistry().runtime_identity(DEMO_AGENT_ID),
        available_tools=["run_shell_command"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="google_adk_test",
    )
    session.start_turn("Show me the current directory.")

    result = session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_owned",
    )

    assert result.trace.source.workspace_id == DEMO_WORKSPACE_ID
    assert result.trace.source.agent_id == DEMO_AGENT_ID
    assert result.trace.source.deployment_id == DEMO_DEPLOYMENT_ID
    assert result.trace.source.integration_id == DEMO_INTEGRATION_ID
    assert result.feature.agent_id == DEMO_AGENT_ID
    assert result.score.agent_id == DEMO_AGENT_ID
    assert result.decision.agent_id == DEMO_AGENT_ID


def test_before_tool_callback_blocks_forbidden_call(monkeypatch, tmp_path):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="gmail_send_email"),
        {"to": "finance@example.com", "body": "Draft body"},
        _fake_tool_context("Draft a reply but do not send it."),
    )

    assert response is not None
    assert response["approval_required"] is False
    assert response["blocked_by_agentguard"] is True
    assert response["runtime_policy"] == "block"
    assert response["firewall_decision"] == "block"


def test_before_tool_callback_always_enforces_explicit_block(monkeypatch, tmp_path):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "false")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="gmail_send_email"),
        {"to": "finance@example.com", "body": "Draft body"},
        _fake_tool_context("Draft a reply but do not send it."),
    )

    assert response is not None
    assert response["runtime_policy"] == "block"
    assert response["blocked_by_agentguard"] is True


def test_before_tool_callback_force_blocks_every_tool_call(monkeypatch, tmp_path):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "false")
    monkeypatch.setenv("AGENTGUARD_FORCE_BLOCK", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "touch should-not-exist"},
        _fake_tool_context("Create a file."),
    )

    assert response is not None
    assert response["approval_required"] is False
    assert response["blocked_by_agentguard"] is True
    assert response["runtime_policy"] == "block"
    assert response["firewall_decision"] == "block"

    decisions = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk" / "decisions.jsonl"
    )
    assert decisions[0]["decision"] == "block"
    assert decisions[0]["decision_rules_fired"] == ["force_block_enabled"]
    assert "force_block_enabled" in decisions[0]["explanation"]

    blocked_events = [
        event
        for event in load_jsonl(
            tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl"
        )
        if event["event_type"] == "tool_blocked"
        and event["payload"].get("runtime_event_source") == "google_adk_adapter"
    ]
    assert len(blocked_events) == 1
    assert blocked_events[0]["payload"]["runtime_policy"] == "block"
    assert blocked_events[0]["payload"]["approval_required"] is False


def test_google_adk_trace_session_records_tool_executed_event(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    result = session.record_tool_call(
        "gmail_search_emails", {"query": "budget"}, call_id="call_search"
    )

    session.record_tool_response(
        "gmail_search_emails",
        {"results": ["thread_budget_q2"]},
        call_id="call_search",
    )

    runtime_events = _runtime_events(tmp_path)
    executed_events = [event for event in runtime_events if event["event_type"] == "tool_executed"]
    assert adk_runtime_policy(result.decision.decision) == "allow"
    assert len(executed_events) == 1
    assert executed_events[0]["payload"]["execution_status"] == "executed"
    assert executed_events[0]["payload"]["runtime_policy"] == "allow"
    assert executed_events[0]["payload"]["firewall_decision"] == result.decision.decision


def test_google_adk_trace_uses_adk_tool_metadata(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")

    result = session.record_tool_call(
        "gmail_search_emails", {"query": "budget"}, call_id="call_search"
    )

    tool = result.trace.proposed_tool_call
    assert tool.tool_category == "email"
    assert tool.risk_level == "read_only"
    assert tool.side_effect_type is None
    assert tool.mcp_server == "gmail"


def test_google_adk_shell_trace_uses_shell_metadata(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Show me the current directory.")

    result = session.record_tool_call("run_shell_command", {"command": "pwd"}, call_id="call_shell")

    tool = result.trace.proposed_tool_call
    assert result.trace.intent.domain == "shell"
    assert tool.tool_category == "shell"
    assert tool.risk_level == "low_side_effect"
    assert tool.side_effect_type == "shell_command"
    assert tool.mcp_server is None


def test_runtime_event_references_persisted_decision(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("gmail_search_emails", {"query": "budget"}, call_id="call_search")

    session.record_tool_response(
        "gmail_search_emails",
        {"results": ["thread_budget_q2"]},
        call_id="call_search",
    )

    decisions = load_jsonl(tmp_path / "traces" / "v1" / "google_adk_test" / "decisions.jsonl")
    decision_ids = {decision["decision_id"] for decision in decisions}
    executed_events = [event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_executed"]
    assert executed_events[0]["payload"]["decision_id"] in decision_ids


def test_google_adk_trace_session_records_tool_failed_event(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("gmail_search_emails", {"query": "budget"}, call_id="call_search")

    session.record_tool_response(
        "gmail_search_emails",
        {"error": "MCP server unavailable"},
        call_id="call_search",
    )

    failed_events = [
        event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_failed"
    ]
    assert len(failed_events) == 1
    assert failed_events[0]["payload"]["execution_status"] == "failed"
    assert failed_events[0]["payload"]["runtime_event_source"] == "google_adk_adapter"


def test_record_tool_response_is_idempotent_for_same_call_id(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("gmail_search_emails", {"query": "budget"}, call_id="call_search")

    session.record_tool_response(
        "gmail_search_emails", {"results": ["thread_budget_q2"]}, call_id="call_search"
    )
    session.record_tool_response(
        "gmail_search_emails", {"results": ["thread_budget_q2"]}, call_id="call_search"
    )

    executed_events = [event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_executed"]
    assert len(executed_events) == 1


def test_record_tool_response_matches_without_call_id(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("gmail_search_emails", {"query": "budget"}, call_id=None)

    session.record_tool_response("gmail_search_emails", {"results": ["thread_budget_q2"]}, call_id=None)

    executed_events = [event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_executed"]
    assert len(executed_events) == 1
    assert executed_events[0]["payload"]["execution_status"] == "executed"


def test_before_tool_callback_allows_normal_shell_command(monkeypatch, tmp_path):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "pwd"},
        _fake_tool_context("Show me the current directory."),
    )

    assert response is None


def test_adk_elastic_override_can_disable_global_elastic(monkeypatch, tmp_path):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "true")
    monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
    monkeypatch.delenv("ELASTICSEARCH_API_KEY", raising=False)
    monkeypatch.setenv("AGENTGUARD_ADK_ELASTIC_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "pwd"},
        _fake_tool_context("Show me the current directory."),
    )

    assert response is None


def test_before_tool_callback_records_approval_blocked_runtime_event(monkeypatch, tmp_path):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    adk_agent._before_tool_callback(
        SimpleNamespace(name="gmail_send_email"),
        {"to": "finance@example.com", "body": "Draft body"},
        _fake_tool_context("Draft a reply but do not send it."),
    )

    blocked_events = [
        event
        for event in load_jsonl(
            tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl"
        )
        if event["event_type"] == "tool_blocked"
        and event["payload"].get("runtime_event_source") == "google_adk_adapter"
    ]
    assert len(blocked_events) == 1
    assert blocked_events[0]["payload"]["execution_status"] == "blocked"
    assert blocked_events[0]["payload"]["approval_required"] is False
    assert blocked_events[0]["payload"]["runtime_policy"] == "block"


def test_adk_callback_uses_registered_dashboard_agent_identity(monkeypatch, tmp_path):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_ADK_ELASTIC_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "pwd"},
        _fake_tool_context("Show me the current directory."),
    )

    trace = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk" / "traces.jsonl"
    )[0]
    assert trace["source"]["workspace_id"] == DEMO_WORKSPACE_ID
    assert trace["source"]["agent_id"] == DEMO_AGENT_ID
    assert trace["source"]["deployment_id"] == DEMO_DEPLOYMENT_ID
    assert trace["source"]["integration_id"] == DEMO_INTEGRATION_ID


def _fake_tool_context(user_text: str):
    return SimpleNamespace(
        session=SimpleNamespace(id="adk_callback_session"),
        invocation_id="adk_callback_invocation",
        agent_name="terminal_assistant",
        user_content=SimpleNamespace(parts=[SimpleNamespace(text=user_text)]),
        function_call_id="call_001",
    )


def _load_adk_agent():
    pytest.importorskip("google.adk", reason="google-adk is an optional runtime dependency")
    module = importlib.import_module("apps.adk_agent.agent")
    return importlib.reload(module)


def _trace_session(tmp_path):
    return GoogleADKTraceSession(
        session_id="adk_test_session",
        agent_id="terminal_assistant",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        available_tools=["run_shell_command", "gmail_search_emails", "gmail_send_email"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="google_adk_test",
        metadata_resolver=_mcp_registry().metadata_for,
    )


def _mcp_registry():
    return McpRegistry.load("config/adk_mcp_servers.toml")


def _runtime_events(tmp_path):
    return [
        event
        for event in load_jsonl(
            tmp_path / "traces" / "v1" / "google_adk_test" / "live_events.jsonl"
        )
        if event["payload"].get("runtime_event_source") == "google_adk_adapter"
    ]
