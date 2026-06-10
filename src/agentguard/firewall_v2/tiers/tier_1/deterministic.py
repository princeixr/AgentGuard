"""Tier 1 deterministic wrapper around the versioned policy evaluator."""

from __future__ import annotations

from time import perf_counter

from agentguard.firewall_v2.policy.evaluator import PolicyEvaluatorV1
from agentguard.firewall_v2.policy.loader import LoadedPolicy
from agentguard.firewall_v2.policy.models import PolicyEvaluationV1
from agentguard.firewall_v2.tiers.models import (
    TierRecommendation,
    TierResultV1,
    TierSignalV1,
)
from agentguard.firewall_v2.tiers.tier_1.agenttrust import (
    AgentTrustShellProvider,
    AgentTrustShellResultV1,
)
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.models import NormalizedActionV1
from agentguard.intent.authorization import authorize_action
from agentguard.intent.models import IntentAuthorizationV1, IntentContractV2
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class Tier1DeterministicEvaluator:
    def __init__(
        self,
        loaded_policy: LoadedPolicy,
        *,
        agenttrust_shell_enabled: bool = True,
        agenttrust_provider: AgentTrustShellProvider | None = None,
        intent_confidence_threshold: float = 0.70,
    ):
        self._policy_evaluator = PolicyEvaluatorV1(loaded_policy)
        self._agenttrust_shell_enabled = agenttrust_shell_enabled
        self._agenttrust_provider = agenttrust_provider or AgentTrustShellProvider()
        self._intent_confidence_threshold = intent_confidence_threshold

    def evaluate(
        self,
        trace: AgentGuardTraceV1,
        descriptor: ToolDescriptorV1,
        action: NormalizedActionV1,
        intent_contract: IntentContractV2 | None = None,
    ) -> tuple[PolicyEvaluationV1, IntentAuthorizationV1 | None, TierResultV1]:
        started = perf_counter()
        policy_evaluation = self._policy_evaluator.evaluate(descriptor, action=action)
        policy_confidence = _confidence(policy_evaluation, action)
        intent_authorization = (
            authorize_action(
                intent_contract,
                action,
                confidence_threshold=self._intent_confidence_threshold,
            )
            if intent_contract is not None
            else None
        )
        agenttrust = self._evaluate_agenttrust(trace, descriptor, action)
        recommendation = _most_restrictive_many(
            policy_evaluation.recommendation,
            (
                intent_authorization.recommendation
                if intent_authorization is not None
                else "not_available"
            ),
            (
                agenttrust.recommendation
                if agenttrust is not None
                else "not_available"
            ),
        )
        confidence = _combined_confidence(policy_confidence, agenttrust)
        signals = [
            TierSignalV1(
                name="deterministic_policy_match",
                score=policy_confidence,
                weight=1.0,
                rationale=policy_evaluation.explanation,
            )
        ]
        if agenttrust is not None:
            signals.append(
                TierSignalV1(
                    name="agenttrust_shell_security",
                    score=agenttrust.confidence,
                    weight=1.0,
                    rationale=agenttrust.explanation,
                )
            )
        if intent_authorization is not None:
            signals.append(
                TierSignalV1(
                    name="turn_intent_authorization",
                    score=intent_contract.extractor.confidence,
                    weight=1.0,
                    rationale=intent_authorization.explanation,
                )
            )
        return policy_evaluation, intent_authorization, TierResultV1(
            tier="tier_1",
            status="completed",
            recommendation=recommendation,
            confidence=confidence,
            signals=signals,
            evidence={
                "policy_evaluation": policy_evaluation.model_dump(mode="json"),
                "normalized_action": action.model_dump(mode="json"),
                "intent_contract": (
                    intent_contract.model_dump(mode="json")
                    if intent_contract is not None
                    else None
                ),
                "intent_authorization": (
                    intent_authorization.model_dump(mode="json")
                    if intent_authorization is not None
                    else None
                ),
                "agenttrust_shell": (
                    agenttrust.model_dump(mode="json") if agenttrust is not None else None
                ),
            },
            escalation_reason=(
                "Tier 1 produced a low-confidence, parser-fallback, or provider-failure result."
                if confidence < 0.75
                else None
            ),
            explanation=_explanation(
                policy_evaluation,
                intent_authorization,
                agenttrust,
                recommendation,
            ),
            latency_ms=int((perf_counter() - started) * 1000),
        )

    def _evaluate_agenttrust(
        self,
        trace: AgentGuardTraceV1,
        descriptor: ToolDescriptorV1,
        action: NormalizedActionV1,
    ) -> AgentTrustShellResultV1 | None:
        if not self._agenttrust_shell_enabled or descriptor.category != "shell":
            return None
        return self._agenttrust_provider.evaluate(trace, descriptor, action)


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


_RECOMMENDATION_PRIORITY: dict[TierRecommendation, int] = {
    "not_available": -1,
    "allow": 0,
    "require_approval": 1,
    "block": 2,
}


def _most_restrictive_many(
    *recommendations: TierRecommendation,
) -> TierRecommendation:
    return max(recommendations, key=_RECOMMENDATION_PRIORITY.__getitem__)


def _combined_confidence(
    policy_confidence: float,
    agenttrust: AgentTrustShellResultV1 | None,
) -> float:
    if agenttrust is None:
        return policy_confidence
    if agenttrust.status == "failed":
        return min(policy_confidence, 0.4)
    return max(policy_confidence, agenttrust.confidence)


def _explanation(
    policy_evaluation: PolicyEvaluationV1,
    intent_authorization: IntentAuthorizationV1 | None,
    agenttrust: AgentTrustShellResultV1 | None,
    recommendation: TierRecommendation,
) -> str:
    if agenttrust is None and intent_authorization is None:
        return policy_evaluation.explanation
    intent_detail = (
        f"Intent authorization: {intent_authorization.explanation} "
        if intent_authorization is not None
        else ""
    )
    agenttrust_detail = (
        f"AgentTrust shell security: {agenttrust.explanation}"
        if agenttrust is not None
        else ""
    )
    return (
        f"Tier 1 selected {recommendation} using restrictive precedence. "
        f"Central policy: {policy_evaluation.explanation} "
        f"{intent_detail}{agenttrust_detail}"
    )
