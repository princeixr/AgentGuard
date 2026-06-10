"""Stateless AgentTrust shell security provider for Tier 1."""

from __future__ import annotations

import re
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
            return _fallback_shell_evaluation(command, reason=str(exc))

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


_DANGEROUS_PATTERNS = [
    r"\|\s*(ba)?sh\b",
    r"\brm\s+-rf\b",
    r"\bsudo\b",
    r"\bchmod\s+777\b",
    r"\bcurl\b.*\|\s*(ba)?sh\b",
    r"\bwget\b.*\|\s*(ba)?sh\b",
    r"\bnc\s+.*\s+-e\b",
    r">\s*/etc/",
]
_ALLOW_PATTERNS = [
    r"^pwd$",
    r"^ls(\s|$)",
    r"^cat\s+[\w./-]+$",
    r"^pytest(\s|$)",
    r"^python\s+-m\s+pytest(\s|$)",
    r"^git\s+status(\s|$)",
]


def _fallback_shell_evaluation(
    command: str,
    *,
    reason: str,
) -> AgentTrustShellResultV1:
    normalized = command.strip()
    if any(re.search(pattern, normalized) for pattern in _DANGEROUS_PATTERNS):
        return AgentTrustShellResultV1(
            provider="agentguard-shell-fallback",
            provider_version="1.0.0",
            status="completed",
            recommendation="block",
            upstream_verdict="block",
            risk_level="high",
            confidence=0.90,
            explanation=(
                "AgentTrust was unavailable, so AgentGuard used its deterministic "
                f"shell fallback and blocked a dangerous command pattern. Cause: {reason}"
            ),
            policy_violations=["dangerous_shell_pattern"],
        )
    if any(re.search(pattern, normalized) for pattern in _ALLOW_PATTERNS):
        return AgentTrustShellResultV1(
            provider="agentguard-shell-fallback",
            provider_version="1.0.0",
            status="completed",
            recommendation="allow",
            upstream_verdict="allow",
            risk_level="low",
            confidence=0.82,
            explanation=(
                "AgentTrust was unavailable, so AgentGuard used its deterministic "
                f"shell fallback and allowed a recognized read/test command. Cause: {reason}"
            ),
        )
    return AgentTrustShellResultV1(
        provider="agentguard-shell-fallback",
        provider_version="1.0.0",
        status="completed",
        recommendation="require_approval",
        upstream_verdict="review",
        risk_level="unknown",
        confidence=0.55,
        explanation=(
            "AgentTrust was unavailable, so AgentGuard used its deterministic shell "
            f"fallback and required approval for an unrecognized command. Cause: {reason}"
        ),
    )
