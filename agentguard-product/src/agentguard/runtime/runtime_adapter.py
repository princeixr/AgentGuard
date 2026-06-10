"""Shared runtime adapter protocol."""

from typing import Protocol

from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class RuntimeAdapter(Protocol):
    def run_session(self, scenario_id: str) -> list[AgentGuardTraceV1]:
        """Runs one scenario and returns emitted canonical v1 traces."""
