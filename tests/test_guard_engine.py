from agentguard.core.enums import ToolRiskLevel, Verdict
from agentguard.core.models import ProposedToolCall, RawTraceRecord, UserIntent
from agentguard.governance.guard_engine import GuardEngine


def test_guard_blocks_or_requires_approval_for_disallowed_send():
    intent = UserIntent(
        session_id="session_001",
        raw_request="Draft a reply, do not send.",
        normalized_intent="Create a draft reply only.",
        allowed_domains=["email"],
        allowed_tools=["gmail_draft"],
        disallowed_tools=["gmail_send"],
        requires_confirmation_for=["gmail_send"],
    )
    proposed = ProposedToolCall(
        call_id="call_001",
        session_id="session_001",
        step_index=1,
        tool_name="gmail_send",
        tool_category="email",
        risk_level=ToolRiskLevel.EXTERNAL_WRITE,
        arguments={"to": "finance@example.com"},
        argument_summary="to=finance@example.com",
        proposed_by="test_agent",
    )
    trace = RawTraceRecord(
        trace_id="trace_001",
        session_id="session_001",
        agent_id="email_agent",
        agent_framework="mock",
        domain="email",
        task_category="email_summary_and_reply",
        user_intent=intent,
        step_index=1,
        proposed_tool_call=proposed,
        execution_status="proposed",
        source_type="synthetic",
    )

    decision = GuardEngine().evaluate(trace)

    assert decision.decision in {Verdict.REQUIRE_APPROVAL, Verdict.BLOCK}
    assert decision.risk_score > 0

