"""Replay stored traces through selected guards."""

from __future__ import annotations

from pathlib import Path

from agentguard.core.models import GuardDecision, RawTraceRecord
from agentguard.evaluation.baseline_guards import build_guard
from agentguard.tracing.serializers import load_jsonl


class TraceReplayRunner:
    def replay(self, trace_file: str | Path, guard_name: str) -> list[GuardDecision]:
        guard = build_guard(guard_name)
        traces = [RawTraceRecord.model_validate(record) for record in load_jsonl(Path(trace_file))]
        return [guard.evaluate(trace) for trace in traces]

