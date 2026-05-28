"""Dashboard view-model helpers."""

from agentguard.core.models import GuardDecision, RawTraceRecord


def session_replay_view(trace: RawTraceRecord, decision: GuardDecision | None = None) -> dict:
    return {
        "trace_id": trace.trace_id,
        "user_intent": trace.user_intent.normalized_intent,
        "tool_name": trace.proposed_tool_call.tool_name,
        "step_index": trace.step_index,
        "decision": decision.decision if decision else None,
        "explanation": decision.explanation if decision else None,
    }

