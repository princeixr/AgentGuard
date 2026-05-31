"""Google ADK adapter placeholder for the hackathon-facing demo."""

from agentguard.governance.firewall_v1 import AgentGuardFirewallV1
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class GoogleADKAdapter:
    def __init__(self, tool_registry=None, firewall=None, trace_builder=None, trace_store=None, max_steps=6):
        self.tool_registry = tool_registry
        self.firewall = firewall or AgentGuardFirewallV1(trace_store=trace_store)
        self.trace_builder = trace_builder
        self.trace_store = trace_store
        self.max_steps = max_steps

    def run_session(self, scenario_id: str) -> list[AgentGuardTraceV1]:
        raise NotImplementedError(
            "Google ADK integration will emit AgentGuardTraceV1 records and call "
            "AgentGuardFirewallV1 before MCP tool execution."
        )
