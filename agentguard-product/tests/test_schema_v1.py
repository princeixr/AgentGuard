import json

from agentguard.core.models import ExecutedToolCall
from agentguard.tracing.schema_v1 import TraceSourceV1
from agentguard.tracing.trace_v1_builder import TraceV1BuildInput, TraceV1Builder


def test_trace_v1_builder_creates_canonical_trace_with_retrieval_text():
    trace = TraceV1Builder().build(
        TraceV1BuildInput(
            session_id="session_001",
            step_index=2,
            source=TraceSourceV1(
                mode="live",
                agent_framework="google_adk",
                source_type="live_google_adk",
                agent_id="google_adk_demo_agent",
            ),
            raw_user_request="Draft a reply. Do not send it.",
            normalized_intent="Create draft reply only.",
            domain="email",
            task_category="email_summary_and_reply",
            tool_name="gmail_send",
            arguments={"draft_id": "draft_001"},
            available_tools=["gmail_search", "gmail_read", "gmail_draft", "gmail_send"],
            task_relevant_tools=["gmail_search", "gmail_read", "gmail_draft"],
            intent_forbidden_tools=["gmail_send"],
            confirmation_required_tools=["gmail_send"],
            prior_tool_calls=[
                ExecutedToolCall(
                    call_id="call_001",
                    session_id="session_001",
                    step_index=1,
                    tool_name="gmail_draft",
                    arguments={"thread_id": "th_budget_q2"},
                    output_summary="Draft created.",
                    status="executed",
                )
            ],
            previous_output_summary="Draft created.",
        )
    )

    payload = json.loads(trace.model_dump_json(by_alias=True))

    assert payload["schema_version"] == "agentguard.trace.v1"
    assert payload["@timestamp"]
    assert payload["intent"]["available_tools"] == [
        "gmail_search",
        "gmail_read",
        "gmail_draft",
        "gmail_send",
    ]
    assert payload["intent"]["task_relevant_tools"] == [
        "gmail_search",
        "gmail_read",
        "gmail_draft",
    ]
    assert payload["intent"]["intent_forbidden_tools"] == ["gmail_send"]
    assert payload["proposed_tool_call"]["risk_level"] == "external_write"
    assert payload["proposed_tool_call"]["argument_hash"].startswith("sha256:")
    assert payload["trajectory"]["prior_tool_sequence"] == "gmail_draft"
    assert "Proposed tool: gmail_send" in payload["retrieval_text"]["summary"]
