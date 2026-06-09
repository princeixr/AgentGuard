"""FirewallV2 deterministic policy evaluation."""

from __future__ import annotations

from collections.abc import Callable

from agentguard.firewall_v2.config import FirewallV2RuntimeConfig
from agentguard.firewall_v2.enforcement import DecisionCombinerV1
from agentguard.firewall_v2.models import FirewallMode, FirewallV2Evaluation, V2StageResult
from agentguard.firewall_v2.policy.loader import LoadedPolicy, PolicyLoader
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy
from agentguard.firewall_v2.tiers.models import TierResultV1
from agentguard.firewall_v2.tiers.tier_1 import Tier1DeterministicEvaluator
from agentguard.firewall_v2.tiers.tier_2 import Tier2SemanticEvaluator
from agentguard.firewall_v2.tiers.tier_3 import Tier3LlmJudge
from agentguard.firewall_v2.tiers.tier_3.judge import LlmJudgeProvider, build_judge_input
from agentguard.firewall_v2.tools.normalizers.registry import normalize_tool_call
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.registry import descriptor_for_tool
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class AgentGuardFirewallV2:
    def __init__(
        self,
        mode: FirewallMode = "v1",
        loaded_policy: LoadedPolicy | None = None,
        runtime_config: FirewallV2RuntimeConfig | None = None,
        tier_3_provider: LlmJudgeProvider | None = None,
        descriptor_resolver: Callable[[str], ToolDescriptorV1] | None = None,
    ):
        self.mode = mode
        self._fixed_policy = loaded_policy
        self._policy_loader = PolicyLoader()
        self.runtime_config = runtime_config or FirewallV2RuntimeConfig.from_env()
        self._tier_3_provider = tier_3_provider
        self._descriptor_resolver = descriptor_resolver

    def evaluate(self, trace: AgentGuardTraceV1) -> FirewallV2Evaluation:
        try:
            return self._evaluate(trace)
        except Exception as exc:
            return FirewallV2Evaluation(
                firewall_mode=self.mode,
                enforcement_status=(
                    "enforced" if self.mode == "v2" else "observe_only"
                ),
                recommendation="block",
                stages=[
                    V2StageResult(
                        name="firewall_v2",
                        status="failed",
                        detail=f"V2 evaluation failed closed: {exc}",
                    )
                ],
                explanation=(
                    "FirewallV2 could not complete evaluation. The fail-closed "
                    "recommendation is block."
                ),
            )

    def _evaluate(self, trace: AgentGuardTraceV1) -> FirewallV2Evaluation:
        loaded_policy = self._fixed_policy or resolve_demo_policy(self._policy_loader)
        descriptor = (
            self._descriptor_resolver(trace.proposed_tool_call.tool_name)
            if self._descriptor_resolver is not None
            else descriptor_for_tool(trace.proposed_tool_call.tool_name)
        )
        normalized_action = normalize_tool_call(trace, descriptor)
        policy_evaluation, tier_1_result = Tier1DeterministicEvaluator(
            loaded_policy
        ).evaluate(
            descriptor,
            normalized_action,
        )
        tier_results: list[TierResultV1] = []
        if self.runtime_config.tier_1_enabled:
            tier_results.append(tier_1_result)
        if self.runtime_config.tier_2_enabled and _should_escalate(
            tier_results,
            self.runtime_config.tier_confidence_threshold,
        ):
            tier_results.append(Tier2SemanticEvaluator().evaluate(trace))
        if self.runtime_config.tier_3_enabled and _should_escalate(
            tier_results,
            self.runtime_config.tier_confidence_threshold,
        ):
            judge_input = build_judge_input(
                trace=trace,
                normalized_action=normalized_action.model_dump(mode="json"),
                policy_evaluation=policy_evaluation.model_dump(mode="json"),
                prior_tier_results=[
                    result.model_dump(mode="json") for result in tier_results
                ],
            )
            tier_results.append(
                Tier3LlmJudge(provider=self._tier_3_provider).evaluate(judge_input)
            )
        combined = DecisionCombinerV1(
            confidence_threshold=self.runtime_config.tier_confidence_threshold,
            tier_3_enforcement_enabled=(
                self.runtime_config.tier_3_enforcement_enabled
            ),
        ).combine(policy_evaluation, tier_results)
        enforcement_status = "enforced" if self.mode == "v2" else "observe_only"
        return FirewallV2Evaluation(
            firewall_mode=self.mode,
            enforcement_status=enforcement_status,
            recommendation=combined.final_decision,
            stages=[
                V2StageResult(
                    name="tool_descriptor",
                    status="completed",
                    detail="Resolved built-in demo tool descriptor.",
                ),
                V2StageResult(
                    name="policy",
                    status="completed",
                    detail=(
                        f"Evaluated {loaded_policy.document.policy_id}@"
                        f"{loaded_policy.document.version}; recommendation="
                        f"{policy_evaluation.recommendation}."
                    ),
                ),
                V2StageResult(
                    name="normalization",
                    status="completed",
                    detail=(
                        f"{normalized_action.parser.name} classified operation="
                        f"{normalized_action.operation}; status="
                        f"{normalized_action.parser.status}."
                    ),
                ),
                V2StageResult(
                    name="intent",
                    status="not_implemented",
                    detail="Intent contracts start in Phase 5.",
                ),
                V2StageResult(
                    name="tier_1",
                    status="completed" if self.runtime_config.tier_1_enabled else "skipped",
                    detail=(
                        "Deterministic policy precedence produced the current "
                        f"recommendation: {policy_evaluation.recommendation}."
                    ),
                ),
                *_tier_stage_results(tier_results),
            ],
            tool_descriptor=descriptor.model_dump(mode="json"),
            normalized_action=normalized_action.model_dump(mode="json"),
            policy_evaluation=policy_evaluation.model_dump(mode="json"),
            tier_results=[result.model_dump(mode="json") for result in tier_results],
            combined_decision=combined.model_dump(mode="json"),
            explanation=(
                (
                    f"FirewallV2 policy recommends and enforces "
                    f"{combined.final_decision}. V1 is retained as "
                    "comparison evidence."
                )
                if self.mode == "v2"
                else (
                    f"FirewallV2 policy recommends {combined.final_decision} "
                    "in observe-only mode. FirewallV1 remains the active enforcement path."
                )
            ),
        )


def _should_escalate(
    tier_results: list[TierResultV1],
    threshold: float,
) -> bool:
    if not tier_results:
        return True
    latest = tier_results[-1]
    if latest.status != "completed":
        return True
    if latest.recommendation == "not_available":
        return True
    return latest.confidence < threshold


def _tier_stage_results(tier_results: list[TierResultV1]) -> list[V2StageResult]:
    existing = {"tier_1"}
    stages = []
    for result in tier_results:
        if result.tier in existing:
            continue
        existing.add(result.tier)
        stages.append(
            V2StageResult(
                name=result.tier,
                status=(
                    "completed"
                    if result.status == "completed"
                    else "failed"
                    if result.status == "failed"
                    else "skipped"
                    if result.status == "skipped"
                    else "not_implemented"
                ),
                detail=result.explanation,
            )
        )
    return stages
