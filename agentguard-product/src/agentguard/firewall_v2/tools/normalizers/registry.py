"""Normalizer resolution for registered V2 tool descriptors."""

from __future__ import annotations

from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.models import (
    NormalizedActionV1,
    ParserResultV1,
)
from agentguard.firewall_v2.tools.normalizers.shell import ShellNormalizerV1
from agentguard.firewall_v2.tools.normalizers.structured import (
    StructuredToolNormalizerV1,
)
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


def normalize_tool_call(
    trace: AgentGuardTraceV1,
    descriptor: ToolDescriptorV1,
) -> NormalizedActionV1:
    if descriptor.normalizer == "shell_v1":
        return ShellNormalizerV1().normalize(trace)
    if descriptor.normalizer == "structured_v1":
        return StructuredToolNormalizerV1().normalize(trace, descriptor)
    return NormalizedActionV1(
        trace_id=trace.trace_id,
        tool_name=descriptor.tool_name,
        capabilities=descriptor.capabilities,
        operation="not_normalized",
        side_effect=descriptor.side_effect is not None,
        reversible=descriptor.reversible,
        impact=descriptor.impact if descriptor.impact != "dynamic" else "unknown",
        flags=["normalizer_not_implemented"],
        parser=ParserResultV1(
            name=descriptor.normalizer,
            version="0.0.0",
            status="unsupported",
            confidence=0.0,
            unsupported_syntax=True,
            detail=f"Normalizer {descriptor.normalizer!r} is not implemented.",
        ),
        argument_hash=trace.proposed_tool_call.argument_hash,
    )
