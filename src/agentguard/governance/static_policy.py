"""Static policy checks for obvious tool-use violations."""

from pydantic import BaseModel

from agentguard.core.enums import ToolRiskLevel, Verdict
from agentguard.core.models import RawTraceRecord


class StaticPolicyResult(BaseModel):
    triggered: bool = False
    suggested_verdict: Verdict | None = None
    reason: str | None = None
    risk_delta: float = 0.0
    critical: bool = False


class StaticPolicy:
    def evaluate(self, trace: RawTraceRecord) -> StaticPolicyResult:
        call = trace.proposed_tool_call
        intent = trace.user_intent

        if call.tool_name in intent.disallowed_tools:
            verdict = (
                Verdict.REQUIRE_APPROVAL
                if call.tool_name in intent.requires_confirmation_for
                else Verdict.BLOCK
            )
            return StaticPolicyResult(
                triggered=True,
                suggested_verdict=verdict,
                reason=f"{call.tool_name} is outside the user's allowed tool scope.",
                risk_delta=0.6,
            )

        if call.risk_level == ToolRiskLevel.IRREVERSIBLE:
            return StaticPolicyResult(
                triggered=True,
                suggested_verdict=Verdict.REQUIRE_APPROVAL,
                reason="Irreversible tool calls require explicit approval.",
                risk_delta=0.5,
            )

        if trace.tool_output_context.contains_secret_like_content and call.risk_level in {
            ToolRiskLevel.EXTERNAL_WRITE,
            ToolRiskLevel.HIGH_RISK,
        }:
            return StaticPolicyResult(
                triggered=True,
                suggested_verdict=Verdict.BLOCK,
                reason="Secret-like prior output should not flow into an external write.",
                risk_delta=0.9,
                critical=True,
            )

        if trace.tool_output_context.contains_untrusted_instruction:
            return StaticPolicyResult(
                triggered=True,
                suggested_verdict=Verdict.REVIEW,
                reason="Prior tool output contained an untrusted instruction.",
                risk_delta=0.35,
            )

        return StaticPolicyResult()

