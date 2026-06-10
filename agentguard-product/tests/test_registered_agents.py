from __future__ import annotations

import importlib.util

from fastapi.testclient import TestClient

from agentguard.control_plane.registry import AgentRegistry
from agentguard.demo import generate_demo_fixtures
from agentguard.server.app import create_app


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


def test_registry_loads_sanitized_agent_manifest():
    registry = AgentRegistry()
    agents = registry.list_agents(registry.workspace.workspace_id)

    assert len(agents) == 1
    definition = registry.definition(agents[0].agent_id)
    assert definition is not None
    assert definition.integration_id
    assert definition.tools[0].name == "run_shell_command"
    assert definition.tools[0].input_schema["type"] == "object"
    assert "headers" not in definition.tools[0].model_dump()
    assert "command" not in definition.tools[0].model_dump()


def test_registered_agent_api_is_framework_neutral(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    agents = client.get("/api/v1/agents")

    assert agents.status_code == 200
    agent = agents.json()["items"][0]
    definition = client.get(
        f"/api/v1/agents/{agent['agent_id']}/definition"
    )

    assert definition.status_code == 200
    payload = definition.json()
    assert payload["agent_id"] == agent["agent_id"]
    assert payload["deployment_id"] == agent["deployments"][0]["deployment_id"]
    assert payload["tools"][0]["normalizer"] == "shell_v1"
    assert payload["agent_ui_url"]


def test_agentguard_does_not_host_agent_test_runs(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    agent_id = client.get("/api/v1/agents").json()["items"][0]["agent_id"]

    response = client.post(
        f"/api/v1/agents/{agent_id}/test-runs",
        json={"message": "run a tool"},
    )

    assert response.status_code == 404


def test_agentguard_runtime_has_no_google_adk_or_mcp_dependency():
    assert importlib.util.find_spec("agentguard.integrations.google_adk") is None
    assert importlib.util.find_spec("agentguard.sdk") is None
