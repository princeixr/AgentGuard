"""Local JSONL repository for AgentGuard dashboard reads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    GuardDecisionV1,
    GuardScoreV1,
    LabelRecordV1,
    LiveEventV1,
    ScenarioRecordV1,
    SessionRiskStateV1,
    TraceFeatureV1,
)
from agentguard.tracing.serializers import load_jsonl

ModelT = TypeVar("ModelT", bound=BaseModel)


class LocalDashboardRepository:
    mode = "local"

    def __init__(
        self,
        root: Path | str,
        namespace: str = "demo",
        fallback_reason: str | None = None,
    ):
        self.root = Path(root)
        self.namespace = namespace
        self.fallback_reason = fallback_reason

    @property
    def namespace_root(self) -> Path:
        return self.root / "v1" / self.namespace

    def is_ready(self) -> bool:
        return (self.namespace_root / "manifest.json").exists()

    def traces(self) -> list[AgentGuardTraceV1]:
        return self._load_models("traces.jsonl", AgentGuardTraceV1)

    def features(self) -> list[TraceFeatureV1]:
        return self._load_models("features.jsonl", TraceFeatureV1)

    def scores(self) -> list[GuardScoreV1]:
        return self._load_models("scores.jsonl", GuardScoreV1)

    def decisions(self) -> list[GuardDecisionV1]:
        return self._load_models("decisions.jsonl", GuardDecisionV1)

    def live_events(self) -> list[LiveEventV1]:
        return self._load_models("live_events.jsonl", LiveEventV1)

    def labels(self) -> list[LabelRecordV1]:
        return self._load_models("labels.jsonl", LabelRecordV1)

    def scenarios(self) -> list[ScenarioRecordV1]:
        return self._load_models("scenarios.jsonl", ScenarioRecordV1)

    def session_states(self) -> list[SessionRiskStateV1]:
        state_dir = self.namespace_root / "session_risk"
        if not state_dir.exists():
            return []
        return [
            SessionRiskStateV1.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(state_dir.glob("*.json"))
        ]

    def manifest(self) -> dict:
        path = self.namespace_root / "manifest.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_models(self, name: str, model_type: type[ModelT]) -> list[ModelT]:
        return [
            model_type.model_validate(record)
            for record in load_jsonl(self.namespace_root / name)
        ]
