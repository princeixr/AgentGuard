"""Executes approved tool calls and converts results into execution records."""

from time import perf_counter

from agentguard.core.models import ExecutedToolCall, ProposedToolCall
from agentguard.runtime.tool_registry import ToolRegistry


class ToolExecutor:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def execute(self, proposed_call: ProposedToolCall) -> ExecutedToolCall:
        started = perf_counter()
        tool = self.tool_registry.get(proposed_call.tool_name)
        try:
            output = tool(**proposed_call.arguments)
            status = "executed"
            output_summary = str(output)
        except Exception as exc:  # pragma: no cover - placeholder defensive path
            status = "failed"
            output_summary = f"{type(exc).__name__}: {exc}"
        latency_ms = int((perf_counter() - started) * 1000)
        return ExecutedToolCall(
            call_id=proposed_call.call_id,
            session_id=proposed_call.session_id,
            step_index=proposed_call.step_index,
            tool_name=proposed_call.tool_name,
            arguments=proposed_call.arguments,
            output_summary=output_summary,
            status=status,
            latency_ms=latency_ms,
        )
