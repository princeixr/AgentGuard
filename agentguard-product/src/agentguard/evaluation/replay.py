"""Replay stored canonical v1 traces through selected guards."""

from __future__ import annotations

from pathlib import Path

from agentguard.evaluation.baseline_guards import build_guard
from agentguard.tracing.schema_v1 import GuardDecisionV1, AgentGuardTraceV1
from agentguard.tracing.serializers import load_jsonl


class TraceReplayRunner:
    def replay(self, trace_file: str | Path, guard_name: str) -> list[GuardDecisionV1]:
        guard = build_guard(guard_name)
        traces = [AgentGuardTraceV1.model_validate(record) for record in load_jsonl(Path(trace_file))]
        return [guard.intercept(trace).decision for trace in traces]
