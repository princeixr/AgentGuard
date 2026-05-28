"""Local JSONL trace persistence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from agentguard.core.models import GuardDecision, LabelRecord, RawTraceRecord
from agentguard.tracing.serializers import append_jsonl


class TraceStore(BaseModel):
    root_dir: Path = Path("data/traces")

    def append_raw_trace(self, trace: RawTraceRecord, namespace: str = "mock") -> Path:
        path = self.root_dir / "raw" / namespace / "traces.jsonl"
        append_jsonl(path, trace)
        return path

    def append_label(self, label: LabelRecord) -> Path:
        path = self.root_dir / "labeled" / "labels.jsonl"
        append_jsonl(path, label)
        return path

    def append_guard_decision(self, decision: GuardDecision) -> Path:
        path = self.root_dir / "guard_outputs" / "decisions.jsonl"
        append_jsonl(path, decision)
        return path

