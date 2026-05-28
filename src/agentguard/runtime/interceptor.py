"""Tool-call interception boundary between runtime and governance."""

from agentguard.core.models import GuardDecision, RawTraceRecord


class ToolInterceptor:
    def __init__(self, guard_engine):
        self.guard_engine = guard_engine

    def intercept(self, trace: RawTraceRecord) -> GuardDecision:
        return self.guard_engine.evaluate(trace)

