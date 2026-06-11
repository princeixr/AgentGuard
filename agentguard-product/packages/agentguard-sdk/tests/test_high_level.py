from __future__ import annotations

from agentguard_sdk import AgentGuard, FakeAgentGuardClient, GuardCheck


def test_fake_client_supports_one_call_check():
    client = FakeAgentGuardClient(decision="allow")
    result = client.check(
        GuardCheck(
            agent_id="sdk_bot",
            user_message="Search the web.",
            tool_name="web_search",
            tool_type="web.search",
        )
    )

    assert result.allowed is True
    assert result.decision == "allow"


def test_high_level_register_tool_uses_builtin_metadata(monkeypatch):
    guard = AgentGuard(agent_id="sdk_bot")
    fake = FakeAgentGuardClient(decision="allow")
    guard.client = fake

    manifest = guard.register_tool("send_email", tool_type="email.send")

    assert manifest.annotations["agentguard"]["risk_level"] == "high_risk"
    assert fake.registrations[0].tools[0].annotations["agentguard"]["operation"] == "send"
