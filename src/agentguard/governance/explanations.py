"""Short explanation builder for UI and reports."""

from agentguard.core.models import RawTraceRecord
from agentguard.governance.scoring import ScoreBreakdown
from agentguard.governance.static_policy import StaticPolicyResult


class ExplanationBuilder:
    def build(
        self,
        trace: RawTraceRecord,
        static_result: StaticPolicyResult,
        score: ScoreBreakdown,
    ) -> str:
        if static_result.reason:
            return static_result.reason
        if score.intent_mismatch:
            return (
                f"{trace.proposed_tool_call.tool_name} appears misaligned with "
                "the user's stated intent."
            )
        if score.tool_output_susceptibility:
            return "Prior tool output may have influenced the proposed action."
        return "No high-risk trajectory signal was detected by the placeholder guard."

