"""Maps policy and scoring evidence into a final verdict."""

from pydantic import BaseModel

from agentguard.core.enums import Verdict
from agentguard.governance.scoring import ScoreBreakdown
from agentguard.governance.static_policy import StaticPolicyResult


class DecisionThresholds(BaseModel):
    warn: float = 0.35
    review: float = 0.55
    block: float = 0.75


class DecisionPolicy:
    def __init__(self, thresholds: DecisionThresholds | None = None):
        self.thresholds = thresholds or DecisionThresholds()

    def decide(self, static_result: StaticPolicyResult, score: ScoreBreakdown) -> Verdict:
        if static_result.critical:
            return Verdict.BLOCK
        if static_result.suggested_verdict in {Verdict.BLOCK, Verdict.REQUIRE_APPROVAL}:
            return static_result.suggested_verdict
        if score.final_risk_score >= self.thresholds.block:
            return Verdict.BLOCK
        if score.final_risk_score >= self.thresholds.review:
            return Verdict.REVIEW
        if score.final_risk_score >= self.thresholds.warn:
            return Verdict.WARN
        return static_result.suggested_verdict or Verdict.ALLOW

