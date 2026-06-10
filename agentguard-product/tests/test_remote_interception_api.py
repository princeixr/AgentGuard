from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from agentguard.server.app import create_app


def _registration():
    return {
        "schema_version": "agentguard.agent_registration.v1",
        "workspace_id": "wsp_test",
        "agent_id": "agt_test",
        "deployment_id": "dep_test",
        "integration_id": "int_test",
        "name": "Test Agent",
        "description": "Remote test agent",
        "framework": "google_adk",
        "runtime_version": "test",
        "environment": "test",
        "manifest_version": "test",
        "tools": [
            {
                "schema_version": "agentguard.tool_manifest.v1",
                "name": "run_shell_command",
                "source_name": "run_shell_command",
                "provider": "local_terminal",
                "framework": "google_adk",
                "transport": "native",
                "description": "Execute one shell command.",
                "input_schema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
                "annotations": {
                    "agentguard": {
                        "domain": "shell",
                        "operation": "shell",
                        "capabilities": ["dynamic.shell"],
                        "risk_level": "high_risk",
                        "confidence": 1.0,
                    }
                },
                "metadata_provenance": ["test"],
            }
        ],
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


def test_remote_interception_requires_approval_and_resolves(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTGUARD_AGENTTRUST_SHELL_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_INTENT_LLM_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_TIER_3_ENABLED", "true")
    monkeypatch.setenv("AGENTGUARD_TIER3_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    monkeypatch.setenv("AGENTGUARD_APPROVAL_ROOT", str(tmp_path / "approvals"))
    app = create_app(data_root=tmp_path / "runtime")
    client = TestClient(app)

    response = client.post("/api/v1/agents/register", json=_registration())
    assert response.status_code == 200

    turn = {
        "schema_version": "agentguard.turn_start.v1",
        "workspace_id": "wsp_test",
        "agent_id": "agt_test",
        "deployment_id": "dep_test",
        "integration_id": "int_test",
        "session_id": "sess_test",
        "turn_id": "turn_test",
        "user_request": "Show me the current directory.",
        "manifest_version": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/turns/start", json=turn)
    assert response.status_code == 200
    intent_id = response.json()["intent_id"]

    proposal = {
        "schema_version": "agentguard.tool_proposal.v1",
        "workspace_id": "wsp_test",
        "agent_id": "agt_test",
        "deployment_id": "dep_test",
        "integration_id": "int_test",
        "session_id": "sess_test",
        "turn_id": "turn_test",
        "intent_id": intent_id,
        "call_id": "call_test",
        "tool_name": "run_shell_command",
        "arguments": {"command": "pwd"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/tool-proposals/evaluate", json=proposal)
    assert response.status_code == 200
    decision = response.json()
    assert decision["decision"] in {"allow", "require_approval", "block"}
    if decision["decision"] == "require_approval":
        approval_id = decision["approval_request_id"]
        pending = client.get(f"/api/v1/approvals/{approval_id}")
        assert pending.status_code == 200
        assert pending.json()["status"] == "pending"

        resolved = client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"actor": "pytest"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "approved"
