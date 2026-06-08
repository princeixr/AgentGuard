"""Join canonical AgentGuard records into product-facing view models."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import median

from agentguard.api.models import (
    ComponentHealth,
    HealthResponse,
    MemoryDetail,
    MemoryItem,
    MemoryPage,
    NamedMetric,
    OperationsSummary,
    PrecedentSummary,
    ReplayStep,
    ScenarioList,
    ScenarioSummary,
    SessionDetail,
    SessionSummary,
)
from agentguard.api.repositories.base import DashboardRepository
from agentguard.tracing.schema_v1 import GuardDecisionV1

DECISION_SEVERITY = {
    "allow": 0,
    "warn": 1,
    "review": 2,
    "require_approval": 3,
    "block": 4,
}
INTERVENTION_DECISIONS = {"review", "require_approval", "block"}


class DashboardQueryService:
    def __init__(self, repository: DashboardRepository):
        self.repository = repository

    def health(self) -> HealthResponse:
        ready = self.repository.is_ready()
        return HealthResponse(
            status="operational" if ready else "degraded",
            mode=self.repository.mode,
            components=[
                ComponentHealth(
                    name="API",
                    status="operational",
                    detail="FastAPI process is running.",
                ),
                ComponentHealth(
                    name="Local storage",
                    status=(
                        "operational"
                        if ready and self.repository.mode == "local"
                        else "degraded"
                    ),
                    detail=(
                        str(getattr(self.repository, "namespace_root", "Local fallback"))
                        if self.repository.mode == "local"
                        else "Standby fallback while Elastic is active."
                    ),
                ),
                ComponentHealth(
                    name="Elastic Search",
                    status=(
                        "operational"
                        if ready and self.repository.mode == "elastic"
                        else "degraded"
                    ),
                    detail=(
                        "Active dashboard repository."
                        if self.repository.mode == "elastic"
                        else getattr(
                            self.repository,
                            "fallback_reason",
                            None,
                        )
                        or "Optional in local demo mode."
                    ),
                ),
                ComponentHealth(
                    name="Google ADK",
                    status="operational",
                    detail="Tool callback integration configured for the demo agent.",
                ),
                ComponentHealth(
                    name="Guard engine",
                    status="operational",
                    detail=(
                        "Functional deterministic policy and weighted heuristic scorer "
                        "(v0.1); not a trained production anomaly model."
                    ),
                ),
            ],
        )

    def scenarios(self) -> ScenarioList:
        return ScenarioList(
            items=[
                ScenarioSummary(
                    scenario_id=scenario.scenario_id,
                    domain=scenario.domain,
                    task_category=scenario.task_category,
                    user_request=scenario.user_request,
                    failure_type=scenario.failure_type,
                    gold_final_verdict=scenario.gold_final_verdict,
                )
                for scenario in self.repository.scenarios()
            ]
        )

    def sessions(self, agent_id: str | None = None) -> list[SessionSummary]:
        traces_by_session = self._traces_by_session(agent_id)
        decisions = self._effective_decisions()
        summaries = [
            self._session_summary(session_id, traces, decisions)
            for session_id, traces in traces_by_session.items()
        ]
        return sorted(summaries, key=lambda item: item.updated_at, reverse=True)

    def session(
        self,
        session_id: str,
        agent_id: str | None = None,
    ) -> SessionDetail | None:
        traces = self._traces_by_session(agent_id).get(session_id)
        if not traces:
            return None
        scores = self._by_trace(self.repository.scores())
        decisions = self._effective_decisions()
        events_by_trace = self._events_by_trace()
        steps = []
        for trace in traces:
            score = scores[trace.trace_id]
            decision = decisions[trace.trace_id]
            v2_summary = _v2_summary(events_by_trace.get(trace.trace_id, []))
            runtime_event = next(
                (
                    event
                    for event in reversed(events_by_trace.get(trace.trace_id, []))
                    if event.event_type in {"tool_executed", "tool_blocked", "tool_failed"}
                ),
                None,
            )
            steps.append(
                ReplayStep(
                    trace_id=trace.trace_id,
                    step_index=trace.step_index,
                    timestamp=trace.timestamp,
                    tool_name=trace.proposed_tool_call.tool_name,
                    tool_category=trace.proposed_tool_call.tool_category,
                    arguments=trace.proposed_tool_call.arguments,
                    argument_summary=trace.proposed_tool_call.argument_summary,
                    decision=decision.decision,
                    risk_score=decision.final_risk_score,
                    component_scores=score.component_scores.model_dump(),
                    cumulative_risk=score.cumulative_after.cumulative_session_risk,
                    dominant_signals=score.dominant_signals,
                    rules_fired=decision.decision_rules_fired,
                    explanation=decision.explanation,
                    execution_status=(
                        runtime_event.payload.get("execution_status")
                        if runtime_event
                        else trace.execution.status
                    ),
                    output_summary=(
                        runtime_event.payload.get("output_summary") if runtime_event else None
                    ),
                    enforced_by=v2_summary["enforced_by"],
                    v1_decision=v2_summary["v1_decision"],
                    v2_recommendation=v2_summary["v2_recommendation"],
                    v2_effective_decision=v2_summary["v2_effective_decision"],
                    v2_enforcement_status=v2_summary["v2_enforcement_status"],
                )
            )
        summary = self._session_summary(session_id, traces, decisions)
        final_trace = traces[-1]
        return SessionDetail(
            session=summary,
            steps=steps,
            precedents=self._precedents(final_trace.trace_id, agent_id=agent_id),
        )

    def memory(
        self,
        query: str | None = None,
        agent: str | None = None,
        tool: str | None = None,
        decision: str | None = None,
        risk_min: float | None = None,
        risk_max: float | None = None,
        page: int = 1,
        page_size: int = 25,
        agent_id: str | None = None,
    ) -> MemoryPage:
        items = self._memory_items(agent_id)
        normalized_query = (query or "").strip().lower()
        if normalized_query:
            items = [
                item
                for item in items
                if normalized_query
                in _search_text(
                    item.trace_id,
                    item.session_id,
                    item.agent_id,
                    item.tool_name,
                    item.domain,
                    item.explanation,
                    " ".join(item.labels),
                )
            ]
        if agent:
            items = [item for item in items if item.agent_id == agent]
        if tool:
            items = [item for item in items if item.tool_name == tool]
        if decision:
            items = [item for item in items if item.decision == decision]
        if risk_min is not None:
            items = [item for item in items if item.risk_score >= risk_min]
        if risk_max is not None:
            items = [item for item in items if item.risk_score <= risk_max]

        items.sort(key=lambda item: item.timestamp, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return MemoryPage(
            items=items[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    def memory_detail(
        self,
        trace_id: str,
        agent_id: str | None = None,
    ) -> MemoryDetail | None:
        traces = self._by_id(self._agent_traces(agent_id), "trace_id")
        trace = traces.get(trace_id)
        if trace is None:
            return None
        features = self._by_trace(self.repository.features())
        scores = self._by_trace(self.repository.scores())
        decisions = self._effective_decisions()
        labels = self._by_trace(self.repository.labels())
        item = next(
            item
            for item in self._memory_items(agent_id)
            if item.trace_id == trace_id
        )
        return MemoryDetail(
            item=item,
            trace=trace.model_dump(mode="json", by_alias=True),
            feature=features[trace_id].model_dump(mode="json", by_alias=True),
            score=scores[trace_id].model_dump(mode="json", by_alias=True),
            decision=decisions[trace_id].model_dump(mode="json", by_alias=True),
            label=(
                labels[trace_id].model_dump(mode="json", by_alias=True)
                if trace_id in labels
                else None
            ),
            events=[
                event.model_dump(mode="json", by_alias=True)
                for event in self._events_by_trace().get(trace_id, [])
            ],
            precedents=self._precedents(trace_id, agent_id=agent_id),
        )

    def operations(self, agent_id: str | None = None) -> OperationsSummary:
        traces_list = self._agent_traces(agent_id)
        trace_ids = {trace.trace_id for trace in traces_list}
        decisions = [
            decision
            for decision in self._effective_decisions().values()
            if decision.trace_id in trace_ids
        ]
        traces = self._by_trace(traces_list)
        labels = self._by_trace(self.repository.labels())
        total = len(decisions)
        interventions = [
            item for item in decisions if item.decision in INTERVENTION_DECISIONS
        ]
        blocked = [item for item in decisions if item.decision == "block"]
        latencies = sorted(item.latency_ms for item in decisions)
        risky_tools = Counter(
            traces[item.trace_id].proposed_tool_call.tool_name for item in interventions
        )
        failure_modes = Counter(
            labels[item.trace_id].failure_type
            for item in interventions
            if item.trace_id in labels and labels[item.trace_id].failure_type != "none"
        )
        return OperationsSummary(
            intercepted_calls=total,
            intervention_count=len(interventions),
            intervention_rate=_rate(len(interventions), total),
            blocked_count=len(blocked),
            blocked_rate=_rate(len(blocked), total),
            session_count=len(self._traces_by_session(agent_id)),
            p50_latency_ms=int(median(latencies)) if latencies else 0,
            p95_latency_ms=_percentile(latencies, 0.95),
            riskiest_tools=_named_metrics(risky_tools, len(interventions)),
            failure_modes=_named_metrics(failure_modes, len(interventions)),
            health=self.health().components,
        )

    def _memory_items(self, agent_id: str | None = None) -> list[MemoryItem]:
        traces = self._by_trace(self._agent_traces(agent_id))
        decisions = self._effective_decisions()
        scores = self._by_trace(self.repository.scores())
        labels = self._by_trace(self.repository.labels())
        events_by_trace = self._events_by_trace()
        items = []
        for trace_id, trace in traces.items():
            decision = decisions[trace_id]
            score = scores[trace_id]
            v2_summary = _v2_summary(events_by_trace.get(trace_id, []))
            label_values = list(score.dominant_signals)
            if trace_id in labels and labels[trace_id].failure_type != "none":
                label_values.append(labels[trace_id].failure_type)
            items.append(
                MemoryItem(
                    trace_id=trace_id,
                    session_id=trace.session_id,
                    timestamp=trace.timestamp,
                    agent_id=trace.source.agent_id,
                    agent_framework=trace.source.agent_framework,
                    scenario_id=trace.source.scenario_id,
                    domain=trace.intent.domain,
                    tool_name=trace.proposed_tool_call.tool_name,
                    tool_category=trace.proposed_tool_call.tool_category,
                    risk_score=decision.final_risk_score,
                    decision=decision.decision,
                    labels=sorted(set(label_values)),
                    explanation=decision.explanation,
                    enforced_by=v2_summary["enforced_by"],
                    v1_decision=v2_summary["v1_decision"],
                    v2_recommendation=v2_summary["v2_recommendation"],
                    v2_effective_decision=v2_summary["v2_effective_decision"],
                    v2_enforcement_status=v2_summary["v2_enforcement_status"],
                )
            )
        return items

    def _precedents(
        self,
        trace_id: str,
        limit: int = 3,
        agent_id: str | None = None,
    ) -> list[PrecedentSummary]:
        traces = self._by_trace(self._agent_traces(agent_id))
        decisions = self._effective_decisions()
        target = traces[trace_id]
        candidates = [
            trace
            for candidate_id, trace in traces.items()
            if candidate_id != trace_id
            and trace.intent.domain == target.intent.domain
            and (
                trace.proposed_tool_call.tool_name == target.proposed_tool_call.tool_name
                or trace.proposed_tool_call.tool_category
                == target.proposed_tool_call.tool_category
            )
        ]
        candidates.sort(
            key=lambda trace: (
                DECISION_SEVERITY[decisions[trace.trace_id].decision],
                decisions[trace.trace_id].final_risk_score,
            ),
            reverse=True,
        )
        return [
            PrecedentSummary(
                trace_id=trace.trace_id,
                session_id=trace.session_id,
                scenario_id=trace.source.scenario_id,
                tool_name=trace.proposed_tool_call.tool_name,
                decision=decisions[trace.trace_id].decision,
                risk_score=decisions[trace.trace_id].final_risk_score,
                intent=trace.intent.normalized_intent,
            )
            for trace in candidates[:limit]
        ]

    def _session_summary(self, session_id, traces, decisions) -> SessionSummary:
        traces = sorted(traces, key=lambda item: item.step_index)
        session_decisions = [decisions[trace.trace_id] for trace in traces]
        final_decision = max(
            session_decisions,
            key=lambda item: DECISION_SEVERITY[item.decision],
        ).decision
        return SessionSummary(
            session_id=session_id,
            scenario_id=traces[0].source.scenario_id,
            agent_id=traces[0].source.agent_id,
            agent_framework=traces[0].source.agent_framework,
            user_intent=traces[0].intent.normalized_intent,
            started_at=traces[0].timestamp,
            updated_at=traces[-1].timestamp,
            step_count=len(traces),
            final_decision=final_decision,
            max_risk_score=max(item.final_risk_score for item in session_decisions),
            tool_sequence=[trace.proposed_tool_call.tool_name for trace in traces],
        )

    def _traces_by_session(self, agent_id: str | None = None):
        grouped = defaultdict(list)
        for trace in self._agent_traces(agent_id):
            grouped[trace.session_id].append(trace)
        for traces in grouped.values():
            traces.sort(key=lambda item: item.step_index)
        return dict(grouped)

    def _agent_traces(self, agent_id: str | None):
        traces = self.repository.traces()
        completed_trace_ids = (
            {record.trace_id for record in self.repository.features()}
            & {record.trace_id for record in self.repository.scores()}
            & {record.trace_id for record in self.repository.decisions()}
        )
        traces = [
            trace for trace in traces if trace.trace_id in completed_trace_ids
        ]
        if agent_id is None:
            return traces
        return [
            trace for trace in traces if trace.source.agent_id == agent_id
        ]

    def _events_by_trace(self):
        grouped = defaultdict(list)
        for event in self.repository.live_events():
            if event.trace_id:
                grouped[event.trace_id].append(event)
        for events in grouped.values():
            events.sort(key=lambda item: item.timestamp)
        return dict(grouped)

    def _effective_decisions(self) -> dict[str, GuardDecisionV1]:
        decisions = self._by_trace(self.repository.decisions())
        for event in sorted(self.repository.live_events(), key=lambda item: item.timestamp):
            if event.event_type != "firewall_v2_evaluated" or not event.trace_id:
                continue
            payload = event.payload.get("effective_decision")
            if not isinstance(payload, dict):
                continue
            try:
                decisions[event.trace_id] = GuardDecisionV1.model_validate(payload)
            except Exception:
                continue
        return decisions

    @staticmethod
    def _by_trace(records):
        return {record.trace_id: record for record in records}

    @staticmethod
    def _by_id(records, field):
        return {getattr(record, field): record for record in records}


def _rate(value: int, total: int) -> float:
    return value / total if total else 0.0


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    index = max(0, math.ceil(len(values) * percentile) - 1)
    return values[index]


def _named_metrics(counter: Counter, total: int) -> list[NamedMetric]:
    return [
        NamedMetric(name=name, count=count, rate=_rate(count, total))
        for name, count in counter.most_common()
    ]


def _search_text(*values: str) -> str:
    return " ".join(values).lower().replace("_", " ").replace("-", " ")


def _v2_summary(events) -> dict:
    event = next(
        (
            item
            for item in reversed(events)
            if item.event_type == "firewall_v2_evaluated"
        ),
        None,
    )
    if event is None:
        return {
            "enforced_by": "firewall_v1",
            "v1_decision": None,
            "v2_recommendation": None,
            "v2_effective_decision": None,
            "v2_enforcement_status": None,
        }
    payload = event.payload
    evaluation = payload.get("evaluation") or {}
    policy_evaluation = evaluation.get("policy_evaluation") or {}
    v1_decision = (payload.get("v1_decision") or {}).get("decision")
    effective_decision = (payload.get("effective_decision") or {}).get("decision")
    return {
        "enforced_by": str(payload.get("enforced_by") or "firewall_v1"),
        "v1_decision": v1_decision,
        "v2_recommendation": policy_evaluation.get("recommendation"),
        "v2_effective_decision": effective_decision,
        "v2_enforcement_status": evaluation.get("enforcement_status"),
    }
