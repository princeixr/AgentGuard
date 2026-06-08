"""Typed contracts for the first versioned AgentGuard policy format."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PolicyEffect = Literal["allow", "require_approval", "block"]


class StrictPolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyScopeV1(StrictPolicyModel):
    workspace_id: str
    agent_id: str
    deployment_id: str | None = None


class PolicyDefaultsV1(StrictPolicyModel):
    unmatched_tool: PolicyEffect = "block"
    unknown_action: PolicyEffect = "require_approval"
    parser_failure: PolicyEffect = "require_approval"
    semantic_failure: PolicyEffect = "require_approval"
    llm_failure: PolicyEffect = "require_approval"
    no_rule_match: PolicyEffect = "require_approval"


class PolicyMatchV1(StrictPolicyModel):
    capabilities_any: list[str] = Field(default_factory=list)
    tools_any: list[str] = Field(default_factory=list)
    resource_constraints: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_supported_or_declared_predicate(self) -> "PolicyMatchV1":
        if not self.capabilities_any and not self.tools_any and not self.resource_constraints:
            raise ValueError("Policy rule match cannot be empty.")
        return self


class PolicyRuleV1(StrictPolicyModel):
    rule_id: str
    description: str
    effect: PolicyEffect
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    non_overridable: bool = False
    match: PolicyMatchV1


class PolicyRoutingV1(StrictPolicyModel):
    read_only: list[str] = Field(default_factory=lambda: ["tier_1"])
    reversible_side_effect: list[str] = Field(
        default_factory=lambda: ["tier_1", "tier_2"]
    )
    external_or_irreversible: list[str] = Field(
        default_factory=lambda: ["tier_1", "tier_2", "tier_3"]
    )
    ambiguous: list[str] = Field(
        default_factory=lambda: ["tier_1", "tier_2", "tier_3"]
    )


class PolicyDocumentV1(StrictPolicyModel):
    schema_version: Literal["agentguard.policy.v1"]
    policy_id: str
    version: str
    name: str
    description: str
    status: Literal["draft", "published"]
    scope: PolicyScopeV1
    defaults: PolicyDefaultsV1
    routing: PolicyRoutingV1 = Field(default_factory=PolicyRoutingV1)
    rules: list[PolicyRuleV1]
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identity_and_rules(self) -> "PolicyDocumentV1":
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            raise ValueError("Policy version must use semantic version format X.Y.Z.")
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Policy rule IDs must be unique.")
        return self


class PolicyRuleMatchV1(StrictPolicyModel):
    rule_id: str
    effect: PolicyEffect
    description: str
    matched_capabilities: list[str] = Field(default_factory=list)
    matched_resources: list[str] = Field(default_factory=list)


class PolicyEvaluationV1(StrictPolicyModel):
    schema_version: Literal["agentguard.policy_evaluation.v1"] = (
        "agentguard.policy_evaluation.v1"
    )
    policy_id: str
    policy_version: str
    policy_hash: str
    recommendation: PolicyEffect
    matched_rules: list[PolicyRuleMatchV1] = Field(default_factory=list)
    unmatched_capabilities: list[str] = Field(default_factory=list)
    deferred_rule_ids: list[str] = Field(default_factory=list)
    explanation: str
