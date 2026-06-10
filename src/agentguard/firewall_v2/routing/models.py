"""Contracts for an auditable FirewallV2 evaluation plan."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RouteClass = Literal[
    "read_only",
    "reversible_side_effect",
    "external_or_irreversible",
    "ambiguous",
]
TierName = Literal["tier_1", "tier_2", "tier_3"]


class EvaluationPlanV1(BaseModel):
    schema_version: Literal["agentguard.evaluation_plan.v1"] = (
        "agentguard.evaluation_plan.v1"
    )
    route_class: RouteClass
    required_tiers: list[TierName]
    reasons: list[str] = Field(default_factory=list)
    semantic_failure_effect: Literal["allow", "require_approval", "block"]
    llm_failure_effect: Literal["allow", "require_approval", "block"]
    short_circuit_on_deterministic_decision: bool = True
