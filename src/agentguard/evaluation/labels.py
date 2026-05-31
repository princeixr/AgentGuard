"""Label loading helpers."""

from __future__ import annotations

from pathlib import Path

from agentguard.tracing.schema_v1 import LabelRecordV1
from agentguard.tracing.serializers import load_jsonl


def load_labels(path: str | Path) -> list[LabelRecordV1]:
    return [LabelRecordV1.model_validate(record) for record in load_jsonl(Path(path))]
