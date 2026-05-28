"""Google ADK adapter placeholder for the hackathon-facing demo."""

from agentguard.core.models import RawTraceRecord


class GoogleADKAdapter:
    def __init__(self, tool_registry=None, interceptor=None, trace_builder=None, trace_store=None, max_steps=6):
        self.tool_registry = tool_registry
        self.interceptor = interceptor
        self.trace_builder = trace_builder
        self.trace_store = trace_store
        self.max_steps = max_steps

    def run_session(self, scenario_id: str) -> list[RawTraceRecord]:
        raise NotImplementedError("Google ADK integration will be implemented by the runtime track.")

