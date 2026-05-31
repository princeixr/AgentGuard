"""Local JSONL trace persistence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from agentguard.core.models import GuardDecision, LabelRecord, RawTraceRecord
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    GuardDecisionV1,
    GuardScoreV1,
    LabelRecordV1,
    LiveEventV1,
    SessionRiskStateV1,
    TraceFeatureV1,
)
from agentguard.tracing.serializers import append_jsonl


class TraceStore(BaseModel):
    root_dir: Path = Path("data/traces")

    def append_raw_trace(self, trace: RawTraceRecord, namespace: str = "mock") -> Path:
        path = self.root_dir / "raw" / namespace / "traces.jsonl"
        append_jsonl(path, trace)
        return path

    def append_trace_v1(self, trace: AgentGuardTraceV1, namespace: str = "mock") -> Path:
        path = self.root_dir / "v1" / namespace / "traces.jsonl"
        append_jsonl(path, trace)
        return path

    def append_feature_v1(self, feature: TraceFeatureV1, namespace: str = "default") -> Path:
        path = self.root_dir / "v1" / namespace / "features.jsonl"
        append_jsonl(path, feature)
        return path

    def append_score_v1(self, score: GuardScoreV1, namespace: str = "default") -> Path:
        path = self.root_dir / "v1" / namespace / "scores.jsonl"
        append_jsonl(path, score)
        return path

    def append_decision_v1(self, decision: GuardDecisionV1, namespace: str = "default") -> Path:
        path = self.root_dir / "v1" / namespace / "decisions.jsonl"
        append_jsonl(path, decision)
        return path

    def append_live_event_v1(self, event: LiveEventV1, namespace: str = "default") -> Path:
        path = self.root_dir / "v1" / namespace / "live_events.jsonl"
        append_jsonl(path, event)
        return path

    def append_label_v1(self, label: LabelRecordV1, namespace: str = "default") -> Path:
        path = self.root_dir / "v1" / namespace / "labels.jsonl"
        append_jsonl(path, label)
        return path

    def write_session_risk_state_v1(
        self,
        state: SessionRiskStateV1,
        namespace: str = "default",
    ) -> Path:
        path = self.root_dir / "v1" / namespace / "session_risk" / f"{state.session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(state.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        return path

    def append_label(self, label: LabelRecord) -> Path:
        path = self.root_dir / "labeled" / "labels.jsonl"
        append_jsonl(path, label)
        return path

    def append_guard_decision(self, decision: GuardDecision) -> Path:
        path = self.root_dir / "guard_outputs" / "decisions.jsonl"
        append_jsonl(path, decision)
        return path
