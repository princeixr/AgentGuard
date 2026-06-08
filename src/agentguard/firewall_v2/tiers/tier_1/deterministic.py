"""Tier 1 deterministic wrapper around the versioned policy evaluator."""

from __future__ import annotations

from time import perf_counter

from agentguard.firewall_v2.policy.evaluator import PolicyEvaluatorV1
from agentguard.firewall_v2.policy.loader import LoadedPolicy
from agentguard.firewall_v2.policy.models import PolicyEvaluationV1
from agentguard.firewall_v2.tiers.models import TierResultV1, TierSignalV1
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.models import NormalizedActionV1


class Tier1DeterministicEvaluator:
    def __init__(self, loaded_policy: LoadedPolicy):
        self._policy_evaluator = PolicyEvaluatorV1(loaded_policy)

    def evaluate(
        self,
        descriptor: ToolDescriptorV1,
        action: NormalizedActionV1,
    ) -> tuple[PolicyEvaluationV1, TierResultV1]:
        started = perf_counter()
        policy_evaluation = self._policy_evaluator.evaluate(descriptor, action=action)
        confidence = _confidence(policy_evaluation, action)
        return policy_evaluation, TierResultV1(
            tier="tier_1",
            status="completed",
            recommendation=policy_evaluation.recommendation,
            confidence=confidence,
            signals=[
                TierSignalV1(
                    name="deterministic_policy_match",
                    score=confidence,
                    weight=1.0,
                    rationale=policy_evaluation.explanation,
                )
            ],
            evidence={
                "policy_evaluation": policy_evaluation.model_dump(mode="json"),
                "normalized_action": action.model_dump(mode="json"),
            },
            escalation_reason=(
                "Tier 1 produced a low-confidence or parser-fallback result."
                if confidence < 0.75
                else None
            ),
            explanation=policy_evaluation.explanation,
            latency_ms=int((perf_counter() - started) * 1000),
        )


def _confidence(
    policy_evaluation: PolicyEvaluationV1,
    action: NormalizedActionV1,
) -> float:
    if action.parser.status in {"invalid", "unsupported"}:
        return min(0.45, action.parser.confidence)
    if policy_evaluation.matched_rules:
        return max(0.80, action.parser.confidence)
    if policy_evaluation.deferred_rule_ids:
        return 0.60
    return 0.65
