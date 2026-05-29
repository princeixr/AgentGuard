"""OpenClaw trace-agent primitives used by the Python trace collector.

These classes intentionally model the event shape we need from OpenClaw without importing
OpenClaw internals. The real Gateway/App-SDK integration should replace the source of
these events, not the AgentGuard trace contract.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from agentguard.core.models import ScenarioRecord


class OpenClawToolEvent(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output_summary: str | None = None
    source_event_id: str | None = None
    source_tool_call_id: str | None = None
    source_record_index: int | None = None
    contains_untrusted_instruction: bool = False
    contains_external_link: bool = False
    contains_secret_like_content: bool = False
    output_influenced_next_call: bool = False


class OpenClawTraceAgent(Protocol):
    agent_id: str
    domain: str

    def propose_tool_events(self, scenario: ScenarioRecord) -> list[OpenClawToolEvent]:
        """Return the proposed tool events for one scenario."""


def enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)
