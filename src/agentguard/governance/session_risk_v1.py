"""In-memory/local session risk state management for AgentGuard v1."""

from __future__ import annotations

from agentguard.tracing.schema_v1 import (
    GuardDecisionV1,
    GuardScoreV1,
    RecentRiskWindowEntryV1,
    SessionRiskCountersV1,
    SessionRiskStateV1,
    AgentGuardTraceV1,
)
from agentguard.tracing.trace_store import TraceStore


class SessionRiskManagerV1:
    def __init__(
        self,
        trace_store: TraceStore | None = None,
        window_size: int = 5,
        namespace: str = "default",
    ):
        self.trace_store = trace_store
        self.window_size = window_size
        self.namespace = namespace
        self._states: dict[str, SessionRiskStateV1] = {}

    def get(self, session_id: str) -> SessionRiskStateV1 | None:
        state = self._states.get(session_id)
        if state is not None:
            return state
        if self.trace_store is None:
            return None
        path = (
            self.trace_store.root_dir
            / "v1"
            / self.namespace
            / "session_risk"
            / f"{session_id}.json"
        )
        if not path.exists():
            return None
        state = SessionRiskStateV1.model_validate_json(path.read_text(encoding="utf-8"))
        self._states[session_id] = state
        return state

    def update(
        self,
        trace: AgentGuardTraceV1,
        score: GuardScoreV1,
        decision: GuardDecisionV1 | None = None,
        namespace: str = "default",
    ) -> SessionRiskStateV1:
        previous = self._states.get(trace.session_id)
        counters = previous.counters if previous else SessionRiskCountersV1()
        if decision:
            if decision.decision == "require_approval":
                counters.approval_required_count += 1
            if decision.decision == "block":
                counters.blocked_count += 1
        recent = list(previous.recent_window if previous else [])
        recent.append(
            RecentRiskWindowEntryV1(
                trace_id=trace.trace_id,
                tool_name=trace.proposed_tool_call.tool_name,
                intent_drift=score.component_scores.intent_drift,
                step_risk=score.component_scores.step_risk,
            )
        )
        recent = recent[-self.window_size :]
        tool_sequence = list(previous.tool_sequence if previous else [])
        tool_sequence.append(trace.proposed_tool_call.tool_name)
        state = SessionRiskStateV1(
            session_id=trace.session_id,
            workspace_id=trace.source.workspace_id,
            deployment_id=trace.source.deployment_id,
            agent_framework=trace.source.agent_framework,
            agent_id=trace.source.agent_id,
            last_trace_id=trace.trace_id,
            last_score_id=score.score_id,
            last_step_index=trace.step_index,
            tool_sequence=tool_sequence,
            risk_state=score.cumulative_after,
            max_single_step_risk=max(
                previous.max_single_step_risk if previous else 0.0,
                score.component_scores.step_risk,
            ),
            counters=counters,
            recent_window=recent,
        )
        self._states[trace.session_id] = state
        if self.trace_store:
            self.trace_store.write_session_risk_state_v1(state, namespace=namespace)
        return state
