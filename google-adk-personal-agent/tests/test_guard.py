from types import SimpleNamespace

from personal_agent.guard import AgentGuardAdkInterceptor
from personal_agent.settings import ROOT, _resolve_from_root


class FakeClient:
    def __init__(self):
        self.outcomes = []
        self.registrations = []

    def register(self, registration):
        self.registrations.append(registration)

    def start_turn(self, turn):
        return SimpleNamespace(intent_id="intent-1")

    def evaluate(self, proposal):
        return SimpleNamespace(
            decision_id="decision-1",
            decision="allow",
            approval_request_id=None,
            explanation="allowed",
            trace_id="trace-1",
        )

    def report_outcome(self, outcome):
        self.outcomes.append(outcome)


def test_callbacks_accept_current_adk_keyword_arguments():
    client = FakeClient()
    registration = SimpleNamespace(tools=["workspace_calendar_list"])
    interceptor = AgentGuardAdkInterceptor(
        client,
        registration_factory=lambda: registration,
    )
    tool = SimpleNamespace(name="workspace_calendar_events_list")
    context = SimpleNamespace(
        invocation_id="turn-1",
        function_call_id="call-1",
        user_content=SimpleNamespace(
            parts=[SimpleNamespace(text="Check my calendar")]
        ),
    )

    assert (
        interceptor.before_tool(
            tool=tool,
            args={"calendarId": "primary"},
            tool_context=context,
        )
        is None
    )
    assert (
        interceptor.after_tool(
            tool=tool,
            args={"calendarId": "primary"},
            tool_context=context,
            tool_response={"items": []},
        )
        is None
    )
    assert client.outcomes[-1].status == "executed"
    assert client.registrations[-1] is registration

    interceptor.before_tool(tool=tool, args={}, tool_context=context)
    assert (
        interceptor.on_tool_error(
            tool=tool,
            args={},
            tool_context=context,
            error=RuntimeError("calendar unavailable"),
        )
        is None
    )
    assert client.outcomes[-1].status == "failed"


def test_relative_mcp_config_paths_resolve_from_agent_project():
    assert _resolve_from_root("config/adk_mcp_servers.toml") == (
        ROOT / "config/adk_mcp_servers.toml"
    )
