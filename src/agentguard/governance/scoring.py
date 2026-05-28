"""Deterministic placeholder scoring for trajectory risk."""

from pydantic import BaseModel, Field

from agentguard.core.enums import ToolRiskLevel
from agentguard.core.models import RawTraceRecord
from agentguard.governance.retrieval import RetrievalResult
from agentguard.governance.static_policy import StaticPolicyResult


class ScoreBreakdown(BaseModel):
    intent_mismatch: float = 0.0
    sequence_incoherence: float = 0.0
    argument_drift: float = 0.0
    permission_risk: float = 0.0
    data_minimization_risk: float = 0.0
    tool_output_susceptibility: float = 0.0
    blocked_trace_similarity: float = 0.0
    approved_trace_similarity: float = 0.0
    cumulative_drift: float = 0.0
    final_risk_score: float = Field(ge=0.0, le=1.0)


class TrajectoryScorer:
    def score(
        self,
        trace: RawTraceRecord,
        static_result: StaticPolicyResult,
        retrieval_result: RetrievalResult,
        mode: str = "full_agentguard",
    ) -> ScoreBreakdown:
        call = trace.proposed_tool_call
        intent = trace.user_intent

        intent_mismatch = 1.0 if call.tool_name in intent.disallowed_tools else 0.0
        permission_risk = 0.7 if call.risk_level in {
            ToolRiskLevel.EXTERNAL_WRITE,
            ToolRiskLevel.IRREVERSIBLE,
            ToolRiskLevel.HIGH_RISK,
        } else 0.0

        use_trajectory = mode == "full_agentguard"
        sequence_incoherence = 0.3 if use_trajectory and call.tool_name.endswith("_send") else 0.0
        argument_drift = 0.2 if use_trajectory and "private" in call.argument_summary.lower() else 0.0
        data_minimization_risk = 0.2 if use_trajectory and "secret" in call.argument_summary.lower() else 0.0
        tool_output_susceptibility = (
            0.6 if use_trajectory and trace.tool_output_context.contains_untrusted_instruction else 0.0
        )
        blocked_similarity = max([item.similarity for item in retrieval_result.blocked] or [0.0])
        approved_similarity = max([item.similarity for item in retrieval_result.approved] or [0.0])
        cumulative_drift = min(len(trace.prior_tool_calls) * 0.05, 0.4) if use_trajectory else 0.0

        if mode == "rule_only":
            risk = static_result.risk_delta
            blocked_similarity = approved_similarity = 0.0
        elif mode == "stateless_intent":
            risk = 0.6 * intent_mismatch + 0.4 * permission_risk
            blocked_similarity = approved_similarity = cumulative_drift = 0.0
        else:
            risk = (
                0.20 * intent_mismatch
                + 0.15 * sequence_incoherence
                + 0.15 * argument_drift
                + 0.15 * permission_risk
                + 0.10 * data_minimization_risk
                + 0.10 * tool_output_susceptibility
                + 0.10 * blocked_similarity
                - 0.05 * approved_similarity
                + 0.10 * cumulative_drift
                + static_result.risk_delta
            )

        return ScoreBreakdown(
            intent_mismatch=intent_mismatch,
            sequence_incoherence=sequence_incoherence,
            argument_drift=argument_drift,
            permission_risk=permission_risk,
            data_minimization_risk=data_minimization_risk,
            tool_output_susceptibility=tool_output_susceptibility,
            blocked_trace_similarity=blocked_similarity,
            approved_trace_similarity=approved_similarity,
            cumulative_drift=cumulative_drift,
            final_risk_score=max(0.0, min(1.0, risk)),
        )

