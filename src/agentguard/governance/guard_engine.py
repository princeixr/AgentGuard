"""Top-level governance orchestrator."""

from time import perf_counter

from agentguard.core.models import GuardDecision, RawTraceRecord
from agentguard.governance.decision_policy import DecisionPolicy
from agentguard.governance.explanations import ExplanationBuilder
from agentguard.governance.retrieval import TraceRetriever
from agentguard.governance.scoring import TrajectoryScorer
from agentguard.governance.static_policy import StaticPolicy


class GuardEngine:
    def __init__(
        self,
        static_policy: StaticPolicy | None = None,
        retriever: TraceRetriever | None = None,
        scorer: TrajectoryScorer | None = None,
        decision_policy: DecisionPolicy | None = None,
        explanation_builder: ExplanationBuilder | None = None,
        guard_version: str = "agentguard_v0.1",
        mode: str = "full_agentguard",
    ):
        self.static_policy = static_policy or StaticPolicy()
        self.retriever = retriever or TraceRetriever()
        self.scorer = scorer or TrajectoryScorer()
        self.decision_policy = decision_policy or DecisionPolicy()
        self.explanation_builder = explanation_builder or ExplanationBuilder()
        self.guard_version = guard_version
        self.mode = mode

    def evaluate(self, trace: RawTraceRecord) -> GuardDecision:
        started = perf_counter()
        static_result = self.static_policy.evaluate(trace)
        retrieval_result = self.retriever.retrieve_similar(trace)
        score = self.scorer.score(trace, static_result, retrieval_result, mode=self.mode)
        verdict = self.decision_policy.decide(static_result, score)
        latency_ms = int((perf_counter() - started) * 1000)
        return GuardDecision(
            trace_id=trace.trace_id,
            guard_version=self.guard_version,
            decision=verdict,
            tier_used="decision_policy",
            risk_score=score.final_risk_score,
            similarity_to_approved_trace=score.approved_trace_similarity,
            similarity_to_blocked_trace=score.blocked_trace_similarity,
            trajectory_drift_score=score.cumulative_drift,
            argument_novelty_score=score.argument_drift,
            cumulative_session_risk=score.final_risk_score,
            latency_ms=latency_ms,
            explanation=self.explanation_builder.build(trace, static_result, score),
        )

