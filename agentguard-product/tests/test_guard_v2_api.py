from __future__ import annotations

from fastapi.testclient import TestClient

from agentguard.server.app import create_app


def test_guard_check_auto_registers_tool_and_returns_decision(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTGUARD_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "false")
    monkeypatch.setenv("AGENTGUARD_AGENTTRUST_SHELL_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_INTENT_LLM_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_APPROVAL_ROOT", str(tmp_path / "approvals"))
    client = TestClient(create_app(data_root=tmp_path / "runtime"))

    response = client.post(
        "/api/v2/guard/check",
        json={
            "agent_id": "new_user_bot",
            "user_message": "Send Rahul the project update.",
            "tool_name": "send_email",
            "arguments": {
                "to": "rahul@example.com",
                "subject": "Update",
                "body": "Hello",
            },
            "tool_type": "email.send",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_type"] == "email.send"
    assert payload["risk_level"] == "high_risk"
    assert payload["decision"] in {"allow", "require_approval", "block"}
    assert payload["agent_id"] == "new_user_bot"


def test_guard_check_infers_unknown_tool_as_conservative_custom(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTGUARD_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "false")
    monkeypatch.setenv("AGENTGUARD_AGENTTRUST_SHELL_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_INTENT_LLM_ENABLED", "false")
    client = TestClient(create_app(data_root=tmp_path / "runtime"))

    response = client.post(
        "/api/v2/guard/check",
        json={
            "agent_id": "custom_bot",
            "user_message": "Do the thing.",
            "tool_name": "do_the_thing",
            "arguments": {"value": 1},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_type"] == "custom.do_the_thing"
    assert payload["risk_level"] == "high_risk"
