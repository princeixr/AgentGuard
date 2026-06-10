"""Deterministic combiner for tier recommendations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agentguard.firewall_v2.policy.models import PolicyEvaluationV1
from agentguard.firewall_v2.routing.models import EvaluationPlanV1
from agentguard.firewall_v2.tiers.models import TierResultV1


class CombinedDecisionV1(BaseModel):
    schema_version: Literal["agentguard.combined_decision.v1"] = (
        "agentguard.combined_decision.v1"
    )
    final_decision: Literal["allow", "require_approval", "block"]
    enforced_by: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    tier_result_ids: list[str] = Field(default_factory=list)


class DecisionCombinerV1:
    def __init__(
        self,
        confidence_threshold: float = 0.75,
        tier_3_enforcement_enabled: bool = False,
        allow_model_block: bool = False,
    ):
        self.confidence_threshold = confidence_threshold
        self.tier_3_enforcement_enabled = tier_3_enforcement_enabled
        self.allow_model_block = allow_model_block

    def combine(
        self,
        policy_evaluation: PolicyEvaluationV1,
        tier_results: list[TierResultV1],
        evaluation_plan: EvaluationPlanV1 | None = None,
    ) -> CombinedDecisionV1:
        tier_ids = [result.tier_result_id for result in tier_results]
        tier_1 = next(
            (result for result in tier_results if result.tier == "tier_1"),
            None,
        )
        if policy_evaluation.recommendation == "block":
            return CombinedDecisionV1(
                final_decision="block",
                enforced_by="tier_1_deterministic_policy",
                confidence=1.0,
                reasons=[
                    "Deterministic policy recommended block and is non-overridable.",
                    policy_evaluation.explanation,
                ],
                tier_result_ids=tier_ids,
            )
        if tier_1 is not None and tier_1.recommendation == "block":
            return CombinedDecisionV1(
                final_decision="block",
                enforced_by="tier_1_deterministic_security",
                confidence=tier_1.confidence,
                reasons=[
                    "A deterministic Tier 1 security provider recommended block.",
                    tier_1.explanation,
                ],
                tier_result_ids=tier_ids,
            )
        if policy_evaluation.recommendation == "require_approval":
            return CombinedDecisionV1(
                final_decision="require_approval",
                enforced_by="tier_1_deterministic_policy",
                confidence=1.0,
                reasons=[
                    "Deterministic policy requires approval and is non-overridable.",
                    policy_evaluation.explanation,
                ],
                tier_result_ids=tier_ids,
            )
        if tier_1 is not None and tier_1.recommendation == "require_approval":
            return CombinedDecisionV1(
                final_decision="require_approval",
                enforced_by="tier_1_deterministic_security",
                confidence=tier_1.confidence,
                reasons=[
                    "A deterministic Tier 1 security provider requires approval.",
                    tier_1.explanation,
                ],
                tier_result_ids=tier_ids,
            )

        required_tiers = (
            set(evaluation_plan.required_tiers)
            if evaluation_plan is not None
            else set()
        )
        tier_2 = next(
            (result for result in reversed(tier_results) if result.tier == "tier_2"),
            None,
        )
        if "tier_2" in required_tiers and (
            tier_2 is None or tier_2.status != "completed"
        ) and "tier_3" not in required_tiers:
            return CombinedDecisionV1(
                final_decision=(
                    evaluation_plan.semantic_failure_effect
                    if evaluation_plan is not None
                    else "require_approval"
                ),
                enforced_by="router_semantic_failure_fallback",
                confidence=0.0,
                reasons=[
                    "The policy required Tier 2, but no completed semantic result was available."
                ],
                tier_result_ids=tier_ids,
            )
        if not self.tier_3_enforcement_enabled:
            return CombinedDecisionV1(
                final_decision=(
                    tier_1.recommendation
                    if tier_1 is not None and tier_1.recommendation != "not_available"
                    else policy_evaluation.recommendation
                ),
                enforced_by="tier_1_deterministic_security",
                confidence=tier_1.confidence if tier_1 is not None else 0.85,
                reasons=["Tier 3 enforcement is disabled; using deterministic recommendation."],
                tier_result_ids=tier_ids,
            )

        tier_3 = next((result for result in reversed(tier_results) if result.tier == "tier_3"), None)
        if tier_3 is None:
            return CombinedDecisionV1(
                final_decision=(
                    evaluation_plan.llm_failure_effect
                    if evaluation_plan is not None and "tier_3" in required_tiers
                    else policy_evaluation.recommendation
                ),
                enforced_by=(
                    "router_llm_failure_fallback"
                    if evaluation_plan is not None and "tier_3" in required_tiers
                    else "tier_1_deterministic_policy"
                ),
                confidence=0.0 if "tier_3" in required_tiers else 0.75,
                reasons=["No required Tier 3 result was available for enforcement."],
                tier_result_ids=tier_ids,
            )
        if tier_3.status != "completed" or tier_3.confidence < self.confidence_threshold:
            return CombinedDecisionV1(
                final_decision="require_approval",
                enforced_by="combiner_low_confidence_fallback",
                confidence=tier_3.confidence,
                reasons=[
                    "Tier 3 failed or confidence was below threshold; fail closed to approval.",
                    tier_3.explanation,
                ],
                tier_result_ids=tier_ids,
            )
        if tier_3.recommendation == "block" and not self.allow_model_block:
            return CombinedDecisionV1(
                final_decision="require_approval",
                enforced_by="combiner_model_block_capped",
                confidence=tier_3.confidence,
                reasons=[
                    "Tier 3 recommended block, but model-based hard blocking is capped to approval.",
                    tier_3.explanation,
                ],
                tier_result_ids=tier_ids,
            )
        if tier_3.recommendation in {"allow", "require_approval", "block"}:
            return CombinedDecisionV1(
                final_decision=tier_3.recommendation,
                enforced_by="tier_3_llm_judge",
                confidence=tier_3.confidence,
                reasons=[tier_3.explanation],
                tier_result_ids=tier_ids,
            )
        return CombinedDecisionV1(
            final_decision="require_approval",
            enforced_by="combiner_unknown_fallback",
            confidence=0.0,
            reasons=["Tier 3 returned no enforceable recommendation."],
            tier_result_ids=tier_ids,
        )
