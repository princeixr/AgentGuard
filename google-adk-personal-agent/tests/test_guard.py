from types import SimpleNamespace

from personal_agent.guard import AgentGuardAdkInterceptor
from personal_agent.settings import ROOT, _resolve_from_root


class FakeClient:
    def __init__(self):
        self.outcomes = []
        self.registrations = []
        self.turns = []
        self.proposals = []

    def register(self, registration):
        self.registrations.append(registration)

    def start_turn(self, turn):
        self.turns.append(turn)
        return SimpleNamespace(intent_id="intent-1")

    def evaluate(self, proposal):
        self.proposals.append(proposal)
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


def test_each_adk_invocation_gets_a_distinct_agentguard_session():
    client = FakeClient()
    interceptor = AgentGuardAdkInterceptor(client)
    tool = SimpleNamespace(name="run_shell_command")

    first = SimpleNamespace(
        invocation_id="invocation-1",
        function_call_id="call-1",
        session=SimpleNamespace(id="chat-1"),
        user_content=SimpleNamespace(parts=[SimpleNamespace(text="List downloads")]),
    )
    second = SimpleNamespace(
        invocation_id="invocation-2",
        function_call_id="call-2",
        session=SimpleNamespace(id="chat-1"),
        user_content=SimpleNamespace(parts=[SimpleNamespace(text="List books")]),
    )

    interceptor.before_tool(tool=tool, args={"command": "ls"}, tool_context=first)
    interceptor.before_tool(tool=tool, args={"command": "ls books"}, tool_context=second)

    assert client.turns[0].session_id == "chat-1:invocation-1"
    assert client.turns[1].session_id == "chat-1:invocation-2"
    assert client.proposals[0].session_id != client.proposals[1].session_id


def test_relative_mcp_config_paths_resolve_from_agent_project():
    assert _resolve_from_root("config/adk_mcp_servers.toml") == (
        ROOT / "config/adk_mcp_servers.toml"
    )
