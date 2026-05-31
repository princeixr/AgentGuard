"""Mathematical placeholder scorer for AgentGuard v1 features."""

from __future__ import annotations

from uuid import uuid4

from agentguard.tracing.schema_v1 import (
    ComponentScoresV1,
    CumulativeScoresV1,
    GuardScoreV1,
    SessionRiskStateV1,
    TraceFeatureV1,
)


class GuardScorerV1:
    def __init__(self, guard_version: str = "agentguard_v0.1"):
        self.guard_version = guard_version

    def score(
        self,
        feature: TraceFeatureV1,
        previous_state: SessionRiskStateV1 | None = None,
    ) -> GuardScoreV1:
        before = previous_state.risk_state if previous_state else CumulativeScoresV1()
        component = self._component_scores(feature)
        after = self._cumulative_scores(component, before)
        return GuardScoreV1(
            score_id=str(uuid4()),
            trace_id=feature.trace_id,
            feature_id=feature.feature_id,
            session_id=feature.session_id,
            step_index=feature.step_index,
            guard_version=self.guard_version,
            component_scores=component,
            cumulative_before=before,
            cumulative_after=after,
            dominant_signals=_dominant_signals(feature, component),
        )

    def _component_scores(self, feature: TraceFeatureV1) -> ComponentScoresV1:
        policy = feature.policy_features
        context = feature.context_features
        retrieval = feature.retrieval
        stats = feature.historical_statistics

        tool_disallowed = 1.0 if policy.tool_in_intent_forbidden_set else 0.0
        tool_not_relevant = 0.0 if policy.tool_in_task_relevant_set else 1.0
        constraint_violation = 1.0 if policy.explicit_constraint_violated else 0.0
        semantic_mismatch = 1.0 - context.intent_to_tool_similarity
        intent_drift = _clip(
            0.35 * tool_disallowed
            + 0.25 * tool_not_relevant
            + 0.25 * constraint_violation
            + 0.15 * semantic_mismatch
        )

        transition_surprise = 1.0 - stats.tool_given_previous_tool_probability
        blocked_pressure = retrieval.max_blocked_similarity - retrieval.max_approved_similarity
        sequence_deviation = _clip(
            0.35 * stats.sequence_percentile_rarity
            + 0.30 * transition_surprise
            + 0.35 * max(0.0, blocked_pressure)
        )

        scope_violation = 1.0 if policy.data_scope_violation else 0.0
        argument_drift = _clip(0.40 * stats.argument_cluster_distance + 0.60 * scope_violation)

        confirmation_required = 1.0 if policy.requires_confirmation else 0.0
        side_effect = 1.0 if policy.side_effect_present else 0.0
        irreversible = 1.0 if policy.irreversible_side_effect else 0.0
        permission_risk = _clip(
            0.40 * confirmation_required + 0.30 * side_effect + 0.30 * irreversible
        )

        untrusted_instruction = 1.0 if context.untrusted_instruction_present else 0.0
        secret_like = 1.0 if context.secret_like_content_present else 0.0
        tool_output_susceptibility = _clip(
            0.40 * untrusted_instruction
            + 0.25 * secret_like
            + 0.35 * context.previous_output_to_tool_similarity
        )

        retrieval_risk = _clip(
            0.45 * retrieval.max_blocked_similarity
            + 0.30 * retrieval.blocked_neighbor_ratio
            + 0.25 * stats.historical_block_rate_for_tool_intent
            - 0.20 * retrieval.max_approved_similarity
        )

        step_risk = _clip(
            0.25 * intent_drift
            + 0.15 * sequence_deviation
            + 0.15 * argument_drift
            + 0.20 * permission_risk
            + 0.10 * tool_output_susceptibility
            + 0.15 * retrieval_risk
        )

        return ComponentScoresV1(
            intent_drift=intent_drift,
            sequence_deviation=sequence_deviation,
            argument_drift=argument_drift,
            permission_risk=permission_risk,
            tool_output_susceptibility=tool_output_susceptibility,
            retrieval_risk=retrieval_risk,
            step_risk=step_risk,
        )

    def _cumulative_scores(
        self,
        component: ComponentScoresV1,
        before: CumulativeScoresV1,
    ) -> CumulativeScoresV1:
        cumulative_intent = _clip(0.70 * before.cumulative_intent_drift + 0.45 * component.intent_drift)
        cumulative_sequence = _clip(
            0.70 * before.cumulative_sequence_deviation + 0.45 * component.sequence_deviation
        )
        cumulative_argument = _clip(
            0.70 * before.cumulative_argument_drift + 0.45 * component.argument_drift
        )
        cumulative_permission = _clip(
            max(before.cumulative_permission_risk, component.permission_risk)
        )
        cumulative_session = _clip(
            0.30 * cumulative_intent
            + 0.20 * cumulative_sequence
            + 0.15 * cumulative_argument
            + 0.20 * cumulative_permission
            + 0.15 * max(component.step_risk, before.cumulative_session_risk)
        )
        return CumulativeScoresV1(
            cumulative_intent_drift=cumulative_intent,
            cumulative_sequence_deviation=cumulative_sequence,
            cumulative_argument_drift=cumulative_argument,
            cumulative_permission_risk=cumulative_permission,
            cumulative_session_risk=cumulative_session,
            drift_streak=before.drift_streak + 1 if component.intent_drift >= 0.35 else 0,
            high_risk_streak=before.high_risk_streak + 1 if component.step_risk >= 0.60 else 0,
        )


def _dominant_signals(feature: TraceFeatureV1, component: ComponentScoresV1) -> list[str]:
    signals = []
    if feature.policy_features.tool_in_intent_forbidden_set:
        signals.append("tool_in_intent_forbidden_set")
    if feature.policy_features.explicit_constraint_violated:
        signals.append("explicit_constraint_violated")
    if feature.policy_features.requires_confirmation:
        signals.append("requires_confirmation")
    if component.intent_drift >= 0.5:
        signals.append("high_intent_drift")
    if component.permission_risk >= 0.7:
        signals.append("high_permission_risk")
    return signals


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))
