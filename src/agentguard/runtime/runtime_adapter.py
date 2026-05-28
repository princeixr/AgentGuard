"""Shared runtime adapter protocol."""

from typing import Protocol

from agentguard.core.models import RawTraceRecord


class RuntimeAdapter(Protocol):
    def run_session(self, scenario_id: str) -> list[RawTraceRecord]:
        """Runs one scenario and returns emitted raw traces."""

