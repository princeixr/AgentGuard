"""Serialization helpers for AgentGuard JSONL data."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


def model_to_json(model: BaseModel) -> str:
    return model.model_dump_json(by_alias=True)


def append_jsonl(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(model_to_json(model))
        handle.write("\n")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            is_incomplete_tail = index == len(lines) - 1 and not line.endswith("\n")
            if is_incomplete_tail:
                break
            raise
    return records
