"""Dashboard view-model helpers."""

from agentguard.tracing.schema_v1 import AgentGuardTraceV1, GuardDecisionV1


def session_replay_view(trace: AgentGuardTraceV1, decision: GuardDecisionV1 | None = None) -> dict:
    return {
        "trace_id": trace.trace_id,
        "user_intent": trace.intent.normalized_intent,
        "tool_name": trace.proposed_tool_call.tool_name,
        "step_index": trace.step_index,
        "decision": decision.decision if decision else None,
        "explanation": decision.explanation if decision else None,
    }
