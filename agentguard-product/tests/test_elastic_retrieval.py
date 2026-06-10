from agentguard.governance.elastic_retrieval import ElasticTraceRetrievalProvider
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    ExecutionStateV1,
    IntentContractV1,
    RetrievalTextV1,
    ToolCallV1,
    TraceSourceV1,
    TrajectoryV1,
)


class FakeRetrievalStore:
    def search_similar_traces(self, trace, size=8, include_live=False):
        return {
            "hits": {
                "hits": [
                    {"_score": 10.0, "_source": {"trace_id": "trace_blocked"}},
                    {"_score": 5.0, "_source": {"trace_id": "trace_allowed"}},
                    {"_score": 2.5, "_source": {"trace_id": "trace_unlabeled"}},
                ]
            }
        }

    def find_latest_decisions_by_trace_ids(self, trace_ids):
        return {
            "trace_blocked": {"trace_id": "trace_blocked", "decision": "block"},
            "trace_allowed": {"trace_id": "trace_allowed", "decision": "allow"},
        }

    def find_labels_by_trace_ids(self, trace_ids):
        return {}


def test_elastic_retrieval_provider_maps_hits_to_retrieval_features():
    provider = ElasticTraceRetrievalProvider(FakeRetrievalStore())

    retrieval = provider.retrieve(_trace())

    assert retrieval.top_k == 3
    assert retrieval.blocked_trace_ids == ["trace_blocked"]
    assert retrieval.approved_trace_ids == ["trace_allowed"]
    assert retrieval.max_blocked_similarity == 1.0
    assert retrieval.max_approved_similarity == 0.5
    assert retrieval.blocked_neighbor_ratio == 0.5


def _trace() -> AgentGuardTraceV1:
    return AgentGuardTraceV1(
        trace_id="trace_query",
        session_id="session_001",
        step_index=1,
        source=TraceSourceV1(
            mode="live",
            agent_framework="google_adk",
            source_type="live_google_adk",
            agent_id="google_adk_demo_agent",
        ),
        intent=IntentContractV1(
            raw_user_request="Draft but do not send.",
            normalized_intent="Draft but do not send.",
            domain="email",
            task_category="email_summary_and_reply",
            available_tools=["gmail_draft", "gmail_send"],
            task_relevant_tools=["gmail_draft"],
            intent_forbidden_tools=["gmail_send"],
        ),
        proposed_tool_call=ToolCallV1(
            call_id="call_001",
            tool_name="gmail_send",
            tool_category="email",
            risk_level="external_write",
            side_effect_type="external_message_send",
            arguments={"draft_id": "draft_001"},
            argument_summary="draft_id=draft_001",
        ),
        trajectory=TrajectoryV1(prior_tool_names=["gmail_draft"]),
        retrieval_text=RetrievalTextV1(
            summary="Draft but do not send. Proposed gmail_send.",
            intent_text="Draft but do not send.",
            trajectory_text="gmail_draft -> gmail_send",
            argument_text="draft_id=draft_001",
        ),
        execution=ExecutionStateV1(status="proposed"),
    )
