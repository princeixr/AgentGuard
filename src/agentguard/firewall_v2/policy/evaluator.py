"""Deterministic capability-level policy matching for Phase 3 shadow mode."""

from __future__ import annotations

from agentguard.firewall_v2.policy.loader import LoadedPolicy
from agentguard.firewall_v2.policy.models import (
    PolicyEffect,
    PolicyEvaluationV1,
    PolicyRuleMatchV1,
)
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.models import NormalizedActionV1

EFFECT_PRIORITY: dict[PolicyEffect, int] = {
    "allow": 0,
    "require_approval": 1,
    "block": 2,
}


class PolicyEvaluatorV1:
    def __init__(self, loaded_policy: LoadedPolicy):
        self.loaded_policy = loaded_policy

    def evaluate(
        self,
        descriptor: ToolDescriptorV1,
        action: NormalizedActionV1 | None = None,
    ) -> PolicyEvaluationV1:
        policy = self.loaded_policy.document
        if descriptor.metadata_status == "unsupported":
            recommendation = policy.defaults.unmatched_tool
            return PolicyEvaluationV1(
                policy_id=policy.policy_id,
                policy_version=policy.version,
                policy_hash=self.loaded_policy.effective_hash,
                recommendation=recommendation,
                unmatched_capabilities=descriptor.capabilities,
                explanation=(
                    f"Tool {descriptor.tool_name} is not registered. Policy default "
                    f"unmatched_tool={recommendation} applies."
                ),
            )
        if (
            action is not None
            and action.parser.name == "shell_v1"
            and action.parser.status in {"invalid", "unsupported"}
        ):
            recommendation = policy.defaults.parser_failure
            return PolicyEvaluationV1(
                policy_id=policy.policy_id,
                policy_version=policy.version,
                policy_hash=self.loaded_policy.effective_hash,
                recommendation=recommendation,
                unmatched_capabilities=action.capabilities,
                explanation=(
                    f"Normalizer {action.parser.name} could not confidently parse "
                    f"{descriptor.tool_name}. Policy default parser_failure="
                    f"{recommendation} applies."
                ),
            )

        matches: list[PolicyRuleMatchV1] = []
        deferred_rule_ids: list[str] = []
        capabilities = set(action.capabilities if action is not None else descriptor.capabilities)
        for rule in policy.rules:
            matched_capabilities = sorted(
                capabilities.intersection(rule.match.capabilities_any)
            )
            tool_matched = descriptor.tool_name in rule.match.tools_any
            base_match = bool(matched_capabilities or tool_matched)
            if rule.match.resource_constraints:
                resource_match = _match_resource_constraints(
                    action,
                    rule.match.resource_constraints,
                )
                if resource_match is None:
                    if base_match or (
                        not rule.match.capabilities_any and not rule.match.tools_any
                    ):
                        deferred_rule_ids.append(rule.rule_id)
                    continue
                if resource_match and (
                    base_match
                    or (not rule.match.capabilities_any and not rule.match.tools_any)
                ):
                    matches.append(
                        PolicyRuleMatchV1(
                            rule_id=rule.rule_id,
                            effect=rule.effect,
                            description=rule.description,
                            matched_capabilities=matched_capabilities,
                            matched_resources=resource_match,
                        )
                    )
                elif base_match:
                    deferred_rule_ids.append(rule.rule_id)
                continue
            if base_match:
                matches.append(
                    PolicyRuleMatchV1(
                        rule_id=rule.rule_id,
                        effect=rule.effect,
                        description=rule.description,
                        matched_capabilities=matched_capabilities,
                    )
                )

        if not matches:
            recommendation = policy.defaults.no_rule_match
            return PolicyEvaluationV1(
                policy_id=policy.policy_id,
                policy_version=policy.version,
                policy_hash=self.loaded_policy.effective_hash,
                recommendation=recommendation,
                unmatched_capabilities=descriptor.capabilities,
                deferred_rule_ids=deferred_rule_ids,
                explanation=(
                    "No currently evaluable capability or tool rule matched. "
                    f"Policy default no_rule_match={recommendation} applies."
                ),
            )

        recommendation = max(
            (match.effect for match in matches),
            key=EFFECT_PRIORITY.__getitem__,
        )
        matched_ids = ", ".join(match.rule_id for match in matches)
        return PolicyEvaluationV1(
            policy_id=policy.policy_id,
            policy_version=policy.version,
            policy_hash=self.loaded_policy.effective_hash,
            recommendation=recommendation,
            matched_rules=matches,
            deferred_rule_ids=deferred_rule_ids,
            explanation=(
                f"Matched policy rules {matched_ids}; most restrictive effect "
                f"is {recommendation}."
            ),
        )


def _match_resource_constraints(
    action: NormalizedActionV1 | None,
    constraints: dict,
) -> list[str] | None:
    if action is None:
        return None
    if "path_any_under" in constraints:
        configured_paths = constraints.get("path_any_under") or []
        matched = [
            resource.value
            for resource in action.resources
            if resource.type == "filesystem_path"
            and any(_path_is_under(resource.value, prefix) for prefix in configured_paths)
        ]
        return matched
    return None


def _path_is_under(value: str, configured_prefix: str) -> bool:
    import os

    normalized_value = os.path.normpath(os.path.expanduser(value))
    normalized_prefix = os.path.normpath(os.path.expanduser(configured_prefix))
    return normalized_value == normalized_prefix or normalized_value.startswith(
        normalized_prefix + os.sep
    )
