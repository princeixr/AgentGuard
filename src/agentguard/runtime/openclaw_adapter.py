"""OpenClaw adapter placeholder for research trace collection."""

from agentguard.core.models import RawTraceRecord


class OpenClawAdapter:
    def __init__(self, interceptor=None, trace_builder=None, trace_store=None, max_steps=6):
        self.interceptor = interceptor
        self.trace_builder = trace_builder
        self.trace_store = trace_store
        self.max_steps = max_steps

    def run_session(self, scenario_id: str) -> list[RawTraceRecord]:
        raise NotImplementedError("OpenClaw trace collection will be implemented by the runtime track.")

