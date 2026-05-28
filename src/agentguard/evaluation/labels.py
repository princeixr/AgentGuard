"""Label loading helpers."""

from __future__ import annotations

from pathlib import Path

from agentguard.core.models import LabelRecord
from agentguard.tracing.serializers import load_jsonl


def load_labels(path: str | Path) -> list[LabelRecord]:
    return [LabelRecord.model_validate(record) for record in load_jsonl(Path(path))]

