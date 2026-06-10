"""Stateless AgentTrust shell security provider for Tier 1."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from agentguard.firewall_v2.tiers.models import TierRecommendation
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.models import NormalizedActionV1
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class AgentTrustShellResultV1(BaseModel):
    schema_version: Literal["agentguard.agenttrust_shell_result.v1"] = (
        "agentguard.agenttrust_shell_result.v1"
    )
    provider: str = "agent-trust"
    provider_version: str = "0.5.0"
    status: Literal["completed", "failed", "skipped"]
    recommendation: TierRecommendation
    upstream_verdict: str | None = None
    risk_level: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    explanation: str
    policy_violations: list[str] = Field(default_factory=list)
    risk_factors: list[dict[str, Any]] = Field(default_factory=list)
    safe_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    evaluation_ms: float = 0.0


class AgentTrustShellProvider:
    """Evaluate one shell proposal without retaining cross-call session state."""

    def __init__(self, *, benchmark_compatibility_rules: bool = False):
        self.benchmark_compatibility_rules = benchmark_compatibility_rules
        self._interceptor: Any | None = None

    def evaluate(
        self,
        trace: AgentGuardTraceV1,
        descriptor: ToolDescriptorV1,
        action: NormalizedActionV1,
    ) -> AgentTrustShellResultV1:
        if descriptor.category != "shell":
            return AgentTrustShellResultV1(
                status="skipped",
                recommendation="not_available",
                explanation="AgentTrust shell analysis applies only to shell tools.",
            )

        command = trace.proposed_tool_call.arguments.get("command")
        if not isinstance(command, str) or not command.strip():
            return AgentTrustShellResultV1(
                status="failed",
                recommendation="require_approval",
                explanation=(
                    "AgentTrust could not evaluate the shell proposal because the "
                    "command argument was missing."
                ),
            )

        try:
            from agent_trust import Action, ActionType, TrustInterceptor

            if self._interceptor is None:
                self._interceptor = TrustInterceptor(
                    session_tracking=False,
                    safefix=True,
                )
                if self.benchmark_compatibility_rules:
                    self._interceptor.policy.load_benchmark_rules()
            report = self._interceptor.verify(
                Action(
                    action_type=ActionType.SHELL_COMMAND,
                    tool_name=trace.proposed_tool_call.tool_name,
                    description=trace.proposed_tool_call.argument_summary,
                    parameters={
                        **trace.proposed_tool_call.arguments,
                        "normalized_operation": action.operation,
                        "normalized_capabilities": action.capabilities,
                        "normalized_flags": action.flags,
                    },
                    raw_content=command,
                    agent_id=trace.source.agent_id,
                    session_id=trace.session_id,
                )
            )
        except Exception as exc:
            return AgentTrustShellResultV1(
                status="failed",
                recommendation="require_approval",
                explanation=f"AgentTrust shell evaluation failed closed: {exc}",
            )

        verdict = _enum_value(report.verdict)
        return AgentTrustShellResultV1(
            status="completed",
            recommendation=_recommendation(verdict),
            upstream_verdict=verdict,
            risk_level=_enum_value(report.overall_risk),
            confidence=report.confidence,
            explanation=report.explanation,
            policy_violations=list(report.policy_violations),
            risk_factors=[_model_dump(item) for item in report.risk_factors],
            safe_suggestions=[_model_dump(item) for item in report.safe_suggestions],
            evaluation_ms=report.evaluation_ms,
        )


def _recommendation(verdict: str) -> TierRecommendation:
    if verdict == "allow":
        return "allow"
    if verdict == "block":
        return "block"
    if verdict in {"warn", "review"}:
        return "require_approval"
    return "require_approval"


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {"value": str(value)}
