from pathlib import Path

from agentguard.governance.firewall_v1 import AgentGuardFirewallV1
from agentguard.tracing.schema_v1 import TraceSourceV1
from agentguard.tracing.trace_store import TraceStore
from agentguard.tracing.trace_v1_builder import TraceV1BuildInput, TraceV1Builder


def build_trace(tool_name: str, step_index: int = 1, session_id: str = "session_001"):
    return TraceV1Builder().build(
        TraceV1BuildInput(
            session_id=session_id,
            step_index=step_index,
            source=TraceSourceV1(
                mode="live",
                agent_framework="google_adk",
                source_type="live_google_adk",
                agent_id="google_adk_demo_agent",
            ),
            raw_user_request="Summarize the budget thread and draft a reply. Do not send it.",
            normalized_intent="Summarize budget thread and create draft only.",
            domain="email",
            task_category="email_summary_and_reply",
            tool_name=tool_name,
            arguments={"thread_id": "th_budget_q2"} if tool_name == "gmail_draft" else {"draft_id": "draft_001"},
            available_tools=["gmail_search", "gmail_read", "gmail_draft", "gmail_send"],
            task_relevant_tools=["gmail_search", "gmail_read", "gmail_draft"],
            intent_forbidden_tools=["gmail_send"],
            confirmation_required_tools=["gmail_send"],
        )
    )


def test_firewall_v1_allows_task_relevant_draft(tmp_path):
    firewall = AgentGuardFirewallV1(
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="test",
    )

    result = firewall.intercept(build_trace("gmail_draft"))

    assert result.decision.decision in {"allow", "warn"}
    assert result.feature.policy_features.tool_in_task_relevant_set is True
    assert (tmp_path / "traces" / "v1" / "test" / "traces.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "test" / "features.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "test" / "scores.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "test" / "decisions.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "test" / "live_events.jsonl").exists()


def test_firewall_v1_blocks_or_requires_approval_for_forbidden_send(tmp_path):
    firewall = AgentGuardFirewallV1(
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="test",
    )

    result = firewall.intercept(build_trace("gmail_send"))

    assert result.feature.policy_features.tool_in_intent_forbidden_set is True
    assert result.feature.policy_features.explicit_constraint_violated is True
    assert result.decision.decision in {"require_approval", "block"}
    assert "tool_in_intent_forbidden_set" in result.decision.decision_rules_fired


def test_firewall_v1_accumulates_session_risk(tmp_path):
    firewall = AgentGuardFirewallV1(
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="test",
    )

    first = firewall.intercept(build_trace("gmail_send", step_index=1))
    second = firewall.intercept(build_trace("gmail_send", step_index=2))

    assert second.score.cumulative_after.cumulative_session_risk >= (
        first.score.cumulative_after.cumulative_session_risk
    )
    assert second.score.cumulative_after.drift_streak >= 2


def test_session_risk_state_is_written(tmp_path):
    firewall = AgentGuardFirewallV1(
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="test",
    )
    result = firewall.intercept(build_trace("gmail_send"))
    state_path = (
        Path(tmp_path)
        / "traces"
        / "v1"
        / "test"
        / "session_risk"
        / f"{result.session_state_id}.json"
    )

    assert state_path.exists()
