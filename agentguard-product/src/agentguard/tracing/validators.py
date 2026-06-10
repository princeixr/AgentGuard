"""Validation helpers for stored trace artifacts."""

from pathlib import Path

from agentguard.core.models import GuardDecision, LabelRecord, RawTraceRecord
from agentguard.tracing.serializers import load_jsonl


def validate_raw_trace_file(path: Path) -> list[RawTraceRecord]:
    return [RawTraceRecord.model_validate(record) for record in load_jsonl(path)]


def validate_label_file(path: Path) -> list[LabelRecord]:
    return [LabelRecord.model_validate(record) for record in load_jsonl(path)]


def validate_guard_output_file(path: Path) -> list[GuardDecision]:
    return [GuardDecision.model_validate(record) for record in load_jsonl(path)]
