"""Decision policy for AgentGuard v1 scores."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from agentguard.tracing.schema_v1 import (
    DecisionRetrievalEvidenceV1,
    DecisionThresholdsV1,
    GuardDecisionV1,
    GuardScoreV1,
    TraceFeatureV1,
    AgentGuardTraceV1,
)


class DecisionPolicyV1:
    def __init__(
        self,
        thresholds: DecisionThresholdsV1 | None = None,
        force_block: bool = False,
    ):
        self.thresholds = thresholds or DecisionThresholdsV1()
        self.force_block = force_block

    def decide(
        self,
        trace: AgentGuardTraceV1,
        feature: TraceFeatureV1,
        score: GuardScoreV1,
    ) -> GuardDecisionV1:
        started = perf_counter()
        rules = []
        final_risk = max(
            score.component_scores.step_risk,
            score.cumulative_after.cumulative_session_risk,
        )
        decision = "allow"
        tier = "decision_policy"

        if self.force_block:
            rules.append("force_block_enabled")
            decision = "block"
            tier = "static_policy"
        elif feature.policy_features.tool_in_intent_forbidden_set:
            rules.append("tool_in_intent_forbidden_set")
            tier = "static_policy"
            if feature.policy_features.irreversible_side_effect:
                decision = "block"
            else:
                decision = "require_approval"
        elif trace.proposed_tool_call.tool_name in trace.intent.confirmation_required_tools:
            rules.append("tool_requires_confirmation")
            decision = "require_approval"
            tier = "static_policy"
        elif (
            feature.context_features.untrusted_instruction_present
            and feature.policy_features.side_effect_present
        ):
            rules.append("untrusted_output_plus_side_effect")
            decision = "block"
            tier = "static_policy"
        elif feature.policy_features.data_scope_violation:
            rules.append("data_scope_violation")
            decision = "review"
            tier = "static_policy"
        elif score.cumulative_after.cumulative_session_risk >= self.thresholds.block:
            rules.append("cumulative_block_threshold")
            decision = "block"
            tier = "cumulative_risk"
        elif score.cumulative_after.cumulative_session_risk >= self.thresholds.require_approval:
            rules.append("cumulative_approval_threshold")
            decision = "require_approval"
            tier = "cumulative_risk"
        elif final_risk >= self.thresholds.review:
            rules.append("risk_review_threshold")
            decision = "review"
        elif final_risk >= self.thresholds.warn:
            rules.append("risk_warn_threshold")
            decision = "warn"

        latency_ms = int((perf_counter() - started) * 1000)
        return GuardDecisionV1(
            decision_id=str(uuid4()),
            trace_id=trace.trace_id,
            score_id=score.score_id,
            session_id=trace.session_id,
            workspace_id=trace.source.workspace_id,
            agent_id=trace.source.agent_id,
            deployment_id=trace.source.deployment_id,
            step_index=trace.step_index,
            decision=decision,
            tier_used=tier,
            final_risk_score=final_risk,
            thresholds=self.thresholds,
            decision_rules_fired=rules,
            retrieval_evidence=DecisionRetrievalEvidenceV1(
                approved_trace_ids=feature.retrieval.approved_trace_ids,
                blocked_trace_ids=feature.retrieval.blocked_trace_ids,
                top_blocked_similarity=feature.retrieval.max_blocked_similarity,
                top_approved_similarity=feature.retrieval.max_approved_similarity,
            ),
            explanation=_explain(trace, decision, rules, final_risk),
            latency_ms=latency_ms,
        )


def _explain(trace: AgentGuardTraceV1, decision: str, rules: list[str], risk: float) -> str:
    if rules:
        return (
            f"Decision {decision} for {trace.proposed_tool_call.tool_name}; "
            f"risk={risk:.2f}; rules={', '.join(rules)}."
        )
    return f"Decision {decision} for {trace.proposed_tool_call.tool_name}; risk={risk:.2f}."
