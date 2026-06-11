from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from agentguard.server.app import create_app


def test_tool_proposal_decision_is_idempotent_with_cache(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTGUARD_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "false")
    monkeypatch.setenv("AGENTGUARD_CACHE_ENABLED", "true")
    monkeypatch.delenv("AGENTGUARD_REDIS_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_AGENTTRUST_SHELL_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_INTENT_LLM_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_APPROVAL_ROOT", str(tmp_path / "approvals"))
    client = TestClient(create_app(data_root=tmp_path / "runtime"))
    now = datetime.now(timezone.utc).isoformat()

    registration = _registration(now)
    assert client.post("/api/v1/agents/register", json=registration).status_code == 200
    turn = {
        "workspace_id": "wsp_cache",
        "agent_id": "agt_cache",
        "deployment_id": "dep_cache",
        "integration_id": "int_cache",
        "session_id": "sess_cache",
        "turn_id": "turn_cache",
        "user_request": "Send Rahul a project update.",
        "manifest_version": "test",
        "timestamp": now,
    }
    intent_id = client.post("/api/v1/turns/start", json=turn).json()["intent_id"]
    proposal = {
        "workspace_id": "wsp_cache",
        "agent_id": "agt_cache",
        "deployment_id": "dep_cache",
        "integration_id": "int_cache",
        "session_id": "sess_cache",
        "turn_id": "turn_cache",
        "intent_id": intent_id,
        "call_id": "call_cache",
        "tool_name": "send_gmail",
        "arguments": {"to": "rahul@example.com", "subject": "Cache", "body": "Hello"},
        "timestamp": now,
    }

    first = client.post("/api/v1/tool-proposals/evaluate", json=proposal).json()
    second = client.post("/api/v1/tool-proposals/evaluate", json=proposal).json()

    assert second["decision_id"] == first["decision_id"]
    assert second["trace_id"] == first["trace_id"]
    assert second["approval_request_id"] == first["approval_request_id"]
    pending = client.get("/api/v1/approvals?status=pending").json()["items"]
    assert [
        item for item in pending if item["approval_id"] == first["approval_request_id"]
    ]


def test_api_rate_limit_uses_cache(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTGUARD_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "false")
    monkeypatch.setenv("AGENTGUARD_CACHE_ENABLED", "true")
    monkeypatch.delenv("AGENTGUARD_REDIS_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("AGENTGUARD_RATE_LIMIT_PER_MINUTE", "2")
    client = TestClient(create_app(data_root=tmp_path / "runtime"))

    assert client.get("/api/v1/agents").status_code == 200
    assert client.get("/api/v1/agents").status_code == 200
    response = client.get("/api/v1/agents")

    assert response.status_code == 429
    assert response.json()["detail"] == "AgentGuard API rate limit exceeded."


def _registration(timestamp: str) -> dict:
    return {
        "workspace_id": "wsp_cache",
        "agent_id": "agt_cache",
        "deployment_id": "dep_cache",
        "integration_id": "int_cache",
        "name": "Cache Agent",
        "description": "Cache runtime test",
        "framework": "google_adk",
        "runtime_version": "test",
        "environment": "test",
        "manifest_version": "test",
        "registered_at": timestamp,
        "tools": [
            {
                "name": "send_gmail",
                "source_name": "send_gmail",
                "provider": "gmail",
                "framework": "google_adk",
                "transport": "native",
                "description": "Send Gmail",
                "input_schema": {"type": "object"},
                "annotations": {
                    "agentguard": {
                        "domain": "email",
                        "operation": "send",
                        "capabilities": ["email.send"],
                        "risk_level": "high_risk",
                    }
                },
            }
        ],
    }
