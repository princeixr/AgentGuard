"""Serialization helpers for AgentGuard JSONL data."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


def model_to_json(model: BaseModel) -> str:
    return model.model_dump_json()


def append_jsonl(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(model_to_json(model))
        handle.write("\n")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]

