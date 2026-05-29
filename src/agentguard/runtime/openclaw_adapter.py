"""Deprecated OpenClaw runtime adapter placeholder.

OpenClaw is not an AgentGuard enforcement runtime in this project. It is a source of
real agent traces for benchmark construction. Use `apps.openclaw_trace_agents` for trace
collection and normalization.
"""

from agentguard.core.models import RawTraceRecord


class OpenClawAdapter:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "OpenClaw is used for offline trace generation, not AgentGuard runtime "
            "enforcement. Use apps.openclaw_trace_agents.trace_collector.OpenClawTraceCollector."
        )

    def run_session(self, scenario_id: str) -> list[RawTraceRecord]:
        raise NotImplementedError("OpenClaw is not used as an AgentGuard runtime adapter.")
