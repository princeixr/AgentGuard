"""FirewallV2 deterministic policy evaluation."""

from __future__ import annotations

from agentguard.firewall_v2.models import FirewallMode, FirewallV2Evaluation, V2StageResult
from agentguard.firewall_v2.policy.evaluator import PolicyEvaluatorV1
from agentguard.firewall_v2.policy.loader import LoadedPolicy, PolicyLoader
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy
from agentguard.firewall_v2.tools.normalizers.registry import normalize_tool_call
from agentguard.firewall_v2.tools.registry import descriptor_for_tool
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class AgentGuardFirewallV2:
    def __init__(
        self,
        mode: FirewallMode = "v1",
        loaded_policy: LoadedPolicy | None = None,
    ):
        self.mode = mode
        self._fixed_policy = loaded_policy
        self._policy_loader = PolicyLoader()

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
        policy_evaluator = PolicyEvaluatorV1(loaded_policy)
        descriptor = descriptor_for_tool(trace.proposed_tool_call.tool_name)
        normalized_action = normalize_tool_call(trace, descriptor)
        policy_evaluation = policy_evaluator.evaluate(
            descriptor,
            action=normalized_action,
        )
        enforcement_status = "enforced" if self.mode == "v2" else "observe_only"
        return FirewallV2Evaluation(
            firewall_mode=self.mode,
            enforcement_status=enforcement_status,
            recommendation=policy_evaluation.recommendation,
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
                    status="completed",
                    detail=(
                        "Deterministic policy precedence produced the current "
                        f"recommendation: {policy_evaluation.recommendation}."
                    ),
                ),
            ],
            tool_descriptor=descriptor.model_dump(mode="json"),
            normalized_action=normalized_action.model_dump(mode="json"),
            policy_evaluation=policy_evaluation.model_dump(mode="json"),
            explanation=(
                (
                    f"FirewallV2 policy recommends and enforces "
                    f"{policy_evaluation.recommendation}. V1 is retained as "
                    "comparison evidence."
                )
                if self.mode == "v2"
                else (
                    f"FirewallV2 policy recommends {policy_evaluation.recommendation} "
                    "in observe-only mode. FirewallV1 remains the active enforcement path."
                )
            ),
        )
