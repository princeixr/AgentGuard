from types import SimpleNamespace

from agentguard_sdk import FakeAgentGuardClient

from personal_agent.agent import build_registration
from personal_agent.guard import AgentGuardAdkInterceptor


def _context():
    return SimpleNamespace(
        invocation_id="turn_1",
        function_call_id="call_1",
        session=SimpleNamespace(id="session_1"),
        user_content=SimpleNamespace(parts=[SimpleNamespace(text="Delete notes.txt")]),
    )


def test_block_prevents_tool_execution_and_reports_outcome():
    client = FakeAgentGuardClient(decision="block")
    interceptor = AgentGuardAdkInterceptor(client)

    result = interceptor.before_tool(
        SimpleNamespace(name="delete_file"),
        {"path": "notes.txt"},
        _context(),
    )

    assert result["blocked_by_agentguard"] is True
    assert client.proposals[0].tool_name == "delete_file"
    assert client.outcomes[0].status == "blocked"


def test_registration_is_sanitized():
    registration = build_registration()
    payload = registration.model_dump(mode="json")

    assert payload["tools"][0]["name"] == "run_shell_command"
    assert "http_headers" not in str(payload)
    assert "stdio_command" not in str(payload)
