from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from agentguard.server.app import create_app
from agentguard.server.models import AgentTestRunResponse
from agentguard.server.services.adk_test import ADKConfigurationError, GoogleADKTestService
from agentguard.control_plane.registry import (
    DEMO_AGENT_ID,
    DEMO_DEPLOYMENT_ID,
    DEMO_INTEGRATION_ID,
    DEMO_WORKSPACE_ID,
    DemoAgentRegistry,
)
from agentguard.demo import generate_demo_fixtures
from agentguard.integrations.google_adk import GoogleADKTraceSession
from agentguard.tracing.trace_store import TraceStore


@pytest.fixture(autouse=True)
def _stable_guard_environment(monkeypatch):
    monkeypatch.setenv("AGENTGUARD_FORCE_BLOCK", "false")
    monkeypatch.setenv("FORCE_BLOCK", "false")
    monkeypatch.setenv("AGENTGUARD_FIREWALL_MODE", "v1")


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "false")
    fixture_root = tmp_path / "fixtures"
    generate_demo_fixtures(fixture_root)
    return TestClient(
        create_app(
            data_root=tmp_path / "runtime",
            fixture_root=fixture_root,
        )
    )


def test_demo_session_and_agent_registry(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    session = client.get("/api/v1/me")
    agents = client.get("/api/v1/agents")

    assert session.status_code == 200
    assert session.json()["workspace"]["workspace_id"] == DEMO_WORKSPACE_ID
    assert session.json()["user"]["role"] == "owner"
    assert agents.status_code == 200
    assert [item["agent_id"] for item in agents.json()["items"]] == [DEMO_AGENT_ID]
    assert agents.json()["items"][0]["deployments"][0]["deployment_id"] == (
        DEMO_DEPLOYMENT_ID
    )


def test_agent_definition_exposes_real_adk_configuration(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get(f"/api/v1/agents/{DEMO_AGENT_ID}/definition")

    assert response.status_code == 200
    definition = response.json()
    assert definition["framework"] == "google_adk"
    assert definition["system_instruction"]
    assert definition["model"]
    assert any(tool["name"] == "run_shell_command" for tool in definition["tools"])
    assert definition["callbacks"]
    assert definition["test_scenarios"]
    shell_tool = next(tool for tool in definition["tools"] if tool["name"] == "run_shell_command")
    assert shell_tool["capabilities"] == ["dynamic.shell"]
    assert shell_tool["normalizer"] == "shell_v1"
    assert shell_tool["metadata_status"] == "built_in"
    assert definition["guardrails"]["policy_id"] == "pol_personal_assistant"
    assert len(definition["guardrails"]["policy_version"].split(".")) == 3
    assert definition["guardrails"]["policy_hash"].startswith("sha256:")
    assert definition["guardrails"]["policy_status"] == "validated_shadow_policy"
    assert definition["guardrails"]["enforced_by"] == "firewall_v1"
    assert definition["guardrails"]["v2_status"] == "not_enabled"


def test_agent_definition_exposes_provider_agnostic_mcp_status(
    tmp_path,
    monkeypatch,
):
    client = _client(tmp_path, monkeypatch)

    definition = client.get(
        f"/api/v1/agents/{DEMO_AGENT_ID}/definition"
    ).json()

    statuses = definition["runtime"]["mcp_servers"]
    assert statuses
    assert {"id", "prefix", "transport", "enabled", "ready", "detail"} <= set(
        statuses[0]
    )
    assert {
        scenario["id"] for scenario in definition["test_scenarios"]
    } == {"inspect_workspace"}


def test_agent_test_route_uses_configured_runtime_service(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    class FakeRuntime:
        async def run(self, message: str) -> AgentTestRunResponse:
            return AgentTestRunResponse(
                run_id="run_test",
                session_id="session_test",
                status="completed",
                model="gemini-test",
                user_message=message,
                final_response="Test response",
                events=[],
                decisions=[],
                duration_ms=5,
            )

    client.app.state.adk_test_service = FakeRuntime()
    response = client.post(
        f"/api/v1/agents/{DEMO_AGENT_ID}/test-runs",
        json={"message": "Hello agent"},
    )

    assert response.status_code == 200
    assert response.json()["user_message"] == "Hello agent"
    assert response.json()["final_response"] == "Test response"


def test_adk_test_service_requires_model_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    service = GoogleADKTestService(repo_root=tmp_path)

    with pytest.raises(ADKConfigurationError):
        asyncio.run(service.run("Hello"))


def test_agent_dashboard_routes_only_return_selected_agent(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    sessions = client.get(f"/api/v1/agents/{DEMO_AGENT_ID}/sessions")
    memory = client.get(f"/api/v1/agents/{DEMO_AGENT_ID}/memory")
    operations = client.get(
        f"/api/v1/agents/{DEMO_AGENT_ID}/operations/summary"
    )

    assert sessions.status_code == 200
    assert sessions.json()
    assert {item["agent_id"] for item in sessions.json()} == {DEMO_AGENT_ID}
    assert memory.status_code == 200
    assert memory.json()["total"] > 0
    assert {item["agent_id"] for item in memory.json()["items"]} == {
        DEMO_AGENT_ID
    }
    assert operations.status_code == 200
    assert operations.json()["intercepted_calls"] == memory.json()["total"]


def test_agent_dashboard_prefers_live_google_adk_records(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "false")
    fixture_root = tmp_path / "fixtures"
    runtime_root = tmp_path / "runtime"
    trace_root = tmp_path / "agent_traces"
    generate_demo_fixtures(fixture_root)
    session = GoogleADKTraceSession(
        session_id="web_live_dashboard_test",
        agent_id=DEMO_AGENT_ID,
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        runtime_identity=DemoAgentRegistry().runtime_identity(DEMO_AGENT_ID),
        available_tools=["run_shell_command"],
        trace_store=TraceStore(root_dir=trace_root),
        namespace="google_adk",
    )
    session.start_turn("Show me the current directory.")
    session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_live_dashboard",
    )
    session.record_tool_response(
        "run_shell_command",
        {"exit_code": 0, "stdout": "/tmp", "stderr": ""},
        call_id="call_live_dashboard",
    )
    client = TestClient(
        create_app(
            data_root=runtime_root,
            fixture_root=fixture_root,
            agent_trace_root=trace_root,
        )
    )

    sessions = client.get(f"/api/v1/agents/{DEMO_AGENT_ID}/sessions")
    memory = client.get(f"/api/v1/agents/{DEMO_AGENT_ID}/memory")
    current = client.get(
        f"/api/v1/agents/{DEMO_AGENT_ID}/interceptions/current"
    )

    assert [item["session_id"] for item in sessions.json()] == [
        "web_live_dashboard_test"
    ]
    assert memory.json()["total"] == 1
    assert current.json()["session_id"] == "web_live_dashboard_test"
    assert current.json()["status"] == "completed"
    assert current.json()["detail"]["item"]["tool_name"] == "run_shell_command"


def test_live_runtime_reconstructs_only_the_latest_historical_event(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "false")
    fixture_root = tmp_path / "fixtures"
    runtime_root = tmp_path / "runtime"
    trace_root = tmp_path / "agent_traces"
    generate_demo_fixtures(fixture_root)
    session = GoogleADKTraceSession(
        session_id="web_bounded_history_test",
        agent_id=DEMO_AGENT_ID,
        runtime_identity=DemoAgentRegistry().runtime_identity(DEMO_AGENT_ID),
        available_tools=["run_shell_command"],
        trace_store=TraceStore(root_dir=trace_root),
        namespace="google_adk",
        firewall_mode="v2",
    )
    session.start_turn("Show me the current directory.")
    session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_bounded_history",
    )
    session.record_tool_response(
        "run_shell_command",
        {"exit_code": 0, "stdout": "/tmp", "stderr": ""},
        call_id="call_bounded_history",
    )
    app = create_app(
        data_root=runtime_root,
        fixture_root=fixture_root,
        agent_trace_root=trace_root,
    )
    query = app.state.query_service
    original_memory_detail = query.memory_detail
    original_session = query.session
    calls = {"memory_detail": 0, "session": 0}

    def counted_memory_detail(*args, **kwargs):
        calls["memory_detail"] += 1
        return original_memory_detail(*args, **kwargs)

    def counted_session(*args, **kwargs):
        calls["session"] += 1
        return original_session(*args, **kwargs)

    monkeypatch.setattr(query, "memory_detail", counted_memory_detail)
    monkeypatch.setattr(query, "session", counted_session)

    current = app.state.agent_live_runtime.current(DEMO_AGENT_ID)

    assert current.status == "completed"
    assert current.session_id == "web_bounded_history_test"
    assert calls == {"memory_detail": 1, "session": 1}


def test_agent_dashboard_surfaces_v2_shadow_live_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_FIREWALL_MODE", "v2_shadow")
    fixture_root = tmp_path / "fixtures"
    runtime_root = tmp_path / "runtime"
    trace_root = tmp_path / "agent_traces"
    generate_demo_fixtures(fixture_root)
    session = GoogleADKTraceSession(
        session_id="web_live_v2_shadow_test",
        agent_id=DEMO_AGENT_ID,
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        runtime_identity=DemoAgentRegistry().runtime_identity(DEMO_AGENT_ID),
        available_tools=["run_shell_command"],
        trace_store=TraceStore(root_dir=trace_root),
        namespace="google_adk",
        firewall_mode="v2_shadow",
    )
    session.start_turn("Show me the current directory.")
    session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_live_v2_shadow",
    )
    session.record_tool_response(
        "run_shell_command",
        {"exit_code": 0, "stdout": "/tmp", "stderr": ""},
        call_id="call_live_v2_shadow",
    )
    client = TestClient(
        create_app(
            data_root=runtime_root,
            fixture_root=fixture_root,
            agent_trace_root=trace_root,
        )
    )

    current = client.get(
        f"/api/v1/agents/{DEMO_AGENT_ID}/interceptions/current"
    ).json()

    assert current["status"] == "completed"
    assert current["event_source"] == "google_adk_runtime"
    assert current["firewall_mode"] == "v2_shadow"
    v2_events = [
        event
        for event in current["detail"]["events"]
        if event["event_type"] == "firewall_v2_evaluated"
    ]
    assert len(v2_events) == 1
    assert v2_events[0]["payload"]["enforced_by"] == "firewall_v1"
    assert v2_events[0]["payload"]["evaluation"]["enforcement_status"] == "observe_only"


def test_agent_live_subscription_streams_v2_event_written_after_connect(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_FIREWALL_MODE", "v2")
    fixture_root = tmp_path / "fixtures"
    runtime_root = tmp_path / "runtime"
    trace_root = tmp_path / "agent_traces"
    generate_demo_fixtures(fixture_root)
    app = create_app(
        data_root=runtime_root,
        fixture_root=fixture_root,
        agent_trace_root=trace_root,
    )
    app.state.agent_live_runtime.poll_interval_seconds = 0.005

    async def exercise():
        runtime = app.state.agent_live_runtime
        subscription = runtime.subscribe(DEMO_AGENT_ID)
        initial = await asyncio.wait_for(anext(subscription), timeout=1)
        session = GoogleADKTraceSession(
            session_id="web_live_sse_v2_test",
            agent_id=DEMO_AGENT_ID,
            runtime_agent_id="terminal_assistant",
            agent_config_id="adk_terminal_assistant",
            runtime_identity=DemoAgentRegistry().runtime_identity(DEMO_AGENT_ID),
            available_tools=["run_shell_command"],
            trace_store=TraceStore(root_dir=trace_root),
            namespace="google_adk",
            firewall_mode="v2",
        )
        session.start_turn("Show me the current directory.")
        session.record_tool_call(
            "run_shell_command",
            {"command": "pwd"},
            call_id="call_live_sse_v2",
        )
        session.record_tool_response(
            "run_shell_command",
            {"exit_code": 0, "stdout": "/tmp", "stderr": ""},
            call_id="call_live_sse_v2",
        )

        envelopes = []
        received_v2_event = False
        received_v2_state = False
        for _ in range(20):
            envelope = await asyncio.wait_for(anext(subscription), timeout=1)
            envelopes.append(envelope)
            received_v2_event = received_v2_event or (
                envelope.event == "live_event"
                and envelope.data["event_type"] == "firewall_v2_evaluated"
            )
            received_v2_state = received_v2_state or (
                envelope.event == "state"
                and envelope.data.get("current_trace_id")
                and envelope.data.get("detail", {})
                .get("item", {})
                .get("guard_evaluation")
                is not None
            )
            if received_v2_event and received_v2_state:
                break

        await subscription.aclose()
        runtime._monitor_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await runtime._monitor_task
        return initial, envelopes

    initial, envelopes = asyncio.run(exercise())

    assert initial.event == "state"
    assert any(
        envelope.event == "live_event"
        and envelope.data["event_type"] == "firewall_v2_evaluated"
        for envelope in envelopes
    )
    latest_state = next(
        envelope for envelope in reversed(envelopes) if envelope.event == "state"
    )
    assert latest_state.data["firewall_mode"] == "v2"
    assert latest_state.data["detail"]["item"]["guard_evaluation"]["recommendation"] == (
        "allow"
    )


def test_agent_dashboard_rejects_unknown_agent_and_scopes_export(
    tmp_path,
    monkeypatch,
):
    client = _client(tmp_path, monkeypatch)

    missing = client.get("/api/v1/agents/agt_unknown/sessions")
    exported = client.get(
        f"/api/v1/agents/{DEMO_AGENT_ID}/operations/export?format=jsonl"
    )

    assert missing.status_code == 404
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/x-ndjson")
    assert f'"agent_id":"{DEMO_AGENT_ID}"' in exported.text
    assert "agt_unknown" not in exported.text


def test_generated_demo_records_have_control_plane_ownership(tmp_path):
    fixture_root = tmp_path / "fixtures"
    generate_demo_fixtures(fixture_root)
    trace_line = (
        fixture_root / "v1" / "demo" / "traces.jsonl"
    ).read_text(encoding="utf-8").splitlines()[0]
    event_line = (
        fixture_root / "v1" / "demo" / "live_events.jsonl"
    ).read_text(encoding="utf-8").splitlines()[0]

    for record in (trace_line, event_line):
        assert DEMO_WORKSPACE_ID in record
        assert DEMO_AGENT_ID in record
        assert DEMO_DEPLOYMENT_ID in record
        assert DEMO_INTEGRATION_ID in record
