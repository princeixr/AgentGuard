"""AgentGuard v1 firewall orchestration.

This is the live governance path for canonical AgentGuardTraceV1 records.
"""

from __future__ import annotations

from uuid import uuid4
from dataclasses import dataclass

from agentguard.governance.decision_policy_v1 import DecisionPolicyV1
from agentguard.governance.elastic_retrieval import ElasticTraceRetrievalProvider
from agentguard.governance.feature_builder_v1 import TraceFeatureBuilderV1
from agentguard.governance.scoring_v1 import GuardScorerV1
from agentguard.governance.session_risk_v1 import SessionRiskManagerV1
from agentguard.storage import AgentGuardElasticStore, load_elastic_config
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    GuardDecisionV1,
    GuardScoreV1,
    LiveEventV1,
    SessionRiskStateV1,
    TraceFeatureV1,
)
from agentguard.tracing.trace_store import TraceStore


@dataclass(frozen=True)
class FirewallResultV1:
    trace: AgentGuardTraceV1
    feature: TraceFeatureV1
    score: GuardScoreV1
    decision: GuardDecisionV1
    session_state_id: str


class AgentGuardFirewallV1:
    def __init__(
        self,
        feature_builder: TraceFeatureBuilderV1 | None = None,
        scorer: GuardScorerV1 | None = None,
        decision_policy: DecisionPolicyV1 | None = None,
        session_risk_manager: SessionRiskManagerV1 | None = None,
        trace_store: TraceStore | None = None,
        elastic_store: AgentGuardElasticStore | None = None,
        enable_elastic: bool | None = None,
        fail_on_elastic_error: bool = True,
        namespace: str = "live",
    ):
        self.trace_store = trace_store or TraceStore()
        self.namespace = namespace
        self.elastic_store = elastic_store or _build_elastic_store(enable_elastic)
        self.fail_on_elastic_error = fail_on_elastic_error
        if feature_builder is None and self.elastic_store is not None:
            feature_builder = TraceFeatureBuilderV1(
                retrieval_provider=ElasticTraceRetrievalProvider(self.elastic_store)
            )
        self.feature_builder = feature_builder or TraceFeatureBuilderV1()
        self.scorer = scorer or GuardScorerV1()
        self.decision_policy = decision_policy or DecisionPolicyV1()
        self.session_risk_manager = session_risk_manager or SessionRiskManagerV1(
            trace_store=self.trace_store,
            namespace=self.namespace,
        )

    def intercept(self, trace: AgentGuardTraceV1) -> FirewallResultV1:
        self.trace_store.append_trace_v1(trace, namespace=self.namespace)
        self._index_trace(trace)
        self._append_event("tool_proposed", trace)

        feature = self.feature_builder.build(trace)
        self.trace_store.append_feature_v1(feature, namespace=self.namespace)
        self._index_feature(feature)

        previous_state = self.session_risk_manager.get(trace.session_id)
        score = self.scorer.score(feature, previous_state=previous_state)
        self.trace_store.append_score_v1(score, namespace=self.namespace)
        self._index_score(score)
        self._append_event("guard_scored", trace, {"score_id": score.score_id})

        decision = self.decision_policy.decide(trace, feature, score)
        self.trace_store.append_decision_v1(decision, namespace=self.namespace)
        self._index_decision(decision)
        self._append_event(
            "guard_decided",
            trace,
            {"decision_id": decision.decision_id, "decision": decision.decision},
        )

        session_state = self.session_risk_manager.update(
            trace=trace,
            score=score,
            decision=decision,
            namespace=self.namespace,
        )
        self._index_session_state(session_state)
        return FirewallResultV1(
            trace=trace,
            feature=feature,
            score=score,
            decision=decision,
            session_state_id=session_state.session_id,
        )

    def _append_event(
        self,
        event_type: str,
        trace: AgentGuardTraceV1,
        payload: dict | None = None,
    ) -> None:
        event = LiveEventV1(
            event_id=str(uuid4()),
            event_type=event_type,
            trace_id=trace.trace_id,
            session_id=trace.session_id,
            step_index=trace.step_index,
            agent_framework=trace.source.agent_framework,
            agent_id=trace.source.agent_id,
            workspace_id=trace.source.workspace_id,
            deployment_id=trace.source.deployment_id,
            integration_id=trace.source.integration_id,
            payload=payload or {},
        )
        self.trace_store.append_live_event_v1(event, namespace=self.namespace)
        self._index_live_event(event)

    def _index_trace(self, trace: AgentGuardTraceV1) -> None:
        if self.elastic_store:
            self._call_elastic(lambda: self.elastic_store.index_trace(trace))

    def _index_feature(self, feature: TraceFeatureV1) -> None:
        if self.elastic_store:
            self._call_elastic(lambda: self.elastic_store.index_trace_feature(feature))

    def _index_score(self, score: GuardScoreV1) -> None:
        if self.elastic_store:
            self._call_elastic(lambda: self.elastic_store.index_guard_score(score))

    def _index_decision(self, decision: GuardDecisionV1) -> None:
        if self.elastic_store:
            self._call_elastic(lambda: self.elastic_store.index_guard_decision(decision))

    def _index_live_event(self, event: LiveEventV1) -> None:
        if self.elastic_store:
            self._call_elastic(lambda: self.elastic_store.index_live_event(event))

    def _index_session_state(self, state: SessionRiskStateV1) -> None:
        if self.elastic_store:
            self._call_elastic(lambda: self.elastic_store.index_session_risk(state))

    def _call_elastic(self, operation) -> None:
        try:
            operation()
        except Exception:
            if self.fail_on_elastic_error:
                raise


def _build_elastic_store(enable_elastic: bool | None) -> AgentGuardElasticStore | None:
    config = load_elastic_config()
    should_enable = config.enabled if enable_elastic is None else enable_elastic
    if not should_enable:
        return None
    config.require_configured()
    return AgentGuardElasticStore(config=config)
