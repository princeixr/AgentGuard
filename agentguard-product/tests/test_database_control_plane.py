from __future__ import annotations

from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from agentguard.server.app import create_app
from agentguard.server.db.api_keys import create_api_key
from agentguard.server.db.session import create_session_factory


def test_database_api_key_and_approval_persistence(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agentguard.sqlite'}"
    monkeypatch.setenv("AGENTGUARD_DATABASE_URL", database_url)
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "true")
    monkeypatch.delenv("AGENTGUARD_API_KEY", raising=False)
    monkeypatch.setenv("AGENTGUARD_AGENTTRUST_SHELL_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_INTENT_LLM_ENABLED", "false")

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    session_factory = create_session_factory()
    assert session_factory is not None
    with session_factory() as session:
        api_key = create_api_key(session, name="pytest").token

    client = TestClient(create_app(data_root=tmp_path / "runtime"))
    headers = {"Authorization": f"Bearer {api_key}"}
    now = datetime.now(timezone.utc).isoformat()
    registration = {
        "workspace_id": "wsp_db",
        "agent_id": "agt_db",
        "deployment_id": "dep_db",
        "integration_id": "int_db",
        "name": "DB Agent",
        "description": "DB persistence test",
        "framework": "google_adk",
        "runtime_version": "test",
        "environment": "test",
        "manifest_version": "test",
        "registered_at": now,
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
    assert client.post("/api/v1/agents/register", json=registration, headers=headers).status_code == 200
    turn = {
        "workspace_id": "wsp_db",
        "agent_id": "agt_db",
        "deployment_id": "dep_db",
        "integration_id": "int_db",
        "session_id": "sess_db",
        "turn_id": "turn_db",
        "user_request": "Send Rahul a project update.",
        "manifest_version": "test",
        "timestamp": now,
    }
    intent_id = client.post("/api/v1/turns/start", json=turn, headers=headers).json()["intent_id"]
    proposal = {
        "workspace_id": "wsp_db",
        "agent_id": "agt_db",
        "deployment_id": "dep_db",
        "integration_id": "int_db",
        "session_id": "sess_db",
        "turn_id": "turn_db",
        "intent_id": intent_id,
        "call_id": "call_db",
        "tool_name": "send_gmail",
        "arguments": {"to": "rahul@example.com", "subject": "DB", "body": "Hello"},
        "timestamp": now,
    }
    decision = client.post(
        "/api/v1/tool-proposals/evaluate",
        json=proposal,
        headers=headers,
    ).json()

    assert decision["decision"] == "require_approval"
    approval_id = decision["approval_request_id"]
    assert approval_id
    pending = client.get("/api/v1/approvals?status=pending", headers=headers).json()
    assert any(item["approval_id"] == approval_id for item in pending["items"])
