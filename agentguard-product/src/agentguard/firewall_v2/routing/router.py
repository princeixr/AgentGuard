"""Build an evaluation plan from normalized action facts and active policy."""

from __future__ import annotations

from typing import cast

from agentguard.firewall_v2.policy.models import PolicyDocumentV1
from agentguard.firewall_v2.routing.models import (
    EvaluationPlanV1,
    RouteClass,
    TierName,
)
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.models import NormalizedActionV1


class EvaluationRouterV1:
    def build_plan(
        self,
        policy: PolicyDocumentV1,
        descriptor: ToolDescriptorV1,
        action: NormalizedActionV1,
    ) -> EvaluationPlanV1:
        route_class, reasons = _classify(descriptor, action)
        configured = getattr(policy.routing, route_class)
        required_tiers = _validated_tiers(configured)
        if "tier_1" not in required_tiers:
            required_tiers.insert(0, "tier_1")
            reasons.append("Tier 1 is mandatory for every intercepted tool call.")
        return EvaluationPlanV1(
            route_class=route_class,
            required_tiers=required_tiers,
            reasons=reasons,
            semantic_failure_effect=policy.defaults.semantic_failure,
            llm_failure_effect=policy.defaults.llm_failure,
        )


def _classify(
    descriptor: ToolDescriptorV1,
    action: NormalizedActionV1,
) -> tuple[RouteClass, list[str]]:
    ambiguity_reasons = []
    if action.parser.status != "parsed":
        ambiguity_reasons.append(f"parser status is {action.parser.status}")
    if action.parser.unsupported_syntax:
        ambiguity_reasons.append("parser reported unsupported syntax")
    if action.parser.confidence < 0.70:
        ambiguity_reasons.append(
            f"parser confidence is {action.parser.confidence:.2f}"
        )
    if descriptor.metadata_status == "unsupported":
        ambiguity_reasons.append("tool metadata is unsupported")
    if descriptor.metadata_confidence < 0.70:
        ambiguity_reasons.append(
            f"tool metadata confidence is {descriptor.metadata_confidence:.2f}"
        )
    if action.operation == "unknown" or not action.capabilities:
        ambiguity_reasons.append("operation or capabilities are unknown")
    if ambiguity_reasons:
        return "ambiguous", ambiguity_reasons

    external_or_irreversible = []
    if action.external_impact is True:
        external_or_irreversible.append("action has external impact")
    if action.reversible is False:
        external_or_irreversible.append("action is irreversible")
    if action.impact == "high":
        external_or_irreversible.append("action impact is high")
    if action.privilege_level not in {"standard", "user"}:
        external_or_irreversible.append(
            f"privilege level is {action.privilege_level}"
        )
    if external_or_irreversible:
        return "external_or_irreversible", external_or_irreversible

    if action.side_effect:
        return (
            "reversible_side_effect",
            ["action has a side effect and is classified as reversible"],
        )
    return "read_only", ["action is read-only and has no side effect"]


def _validated_tiers(configured: list[str]) -> list[TierName]:
    supported = {"tier_1", "tier_2", "tier_3"}
    return [
        cast(TierName, tier)
        for tier in dict.fromkeys(configured)
        if tier in supported
    ]
