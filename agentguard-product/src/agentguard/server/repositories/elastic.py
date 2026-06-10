"""Elastic-backed dashboard repository."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from agentguard.storage import AgentGuardElasticStore
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

ModelT = TypeVar("ModelT", bound=BaseModel)


class ElasticDashboardRepository:
    mode = "elastic"

    def __init__(self, store: AgentGuardElasticStore | None = None):
        self.store = store or AgentGuardElasticStore()

    def is_ready(self) -> bool:
        self.store.ping()
        return True

    def traces(self) -> list[AgentGuardTraceV1]:
        return self._models(self.store.config.indices.traces, AgentGuardTraceV1)

    def features(self) -> list[TraceFeatureV1]:
        return self._models(
            self.store.config.indices.trace_features,
            TraceFeatureV1,
        )

    def scores(self) -> list[GuardScoreV1]:
        return self._models(self.store.config.indices.guard_scores, GuardScoreV1)

    def decisions(self) -> list[GuardDecisionV1]:
        return self._models(
            self.store.config.indices.guard_decisions,
            GuardDecisionV1,
        )

    def live_events(self) -> list[LiveEventV1]:
        return self._models(self.store.config.indices.live_events, LiveEventV1)

    def labels(self) -> list[LabelRecordV1]:
        return self._models(self.store.config.indices.labels, LabelRecordV1)

    def scenarios(self) -> list[ScenarioRecordV1]:
        return self._models(self.store.config.indices.scenarios, ScenarioRecordV1)

    def session_states(self) -> list[SessionRiskStateV1]:
        return self._models(
            self.store.config.indices.session_risk,
            SessionRiskStateV1,
        )

    def manifest(self) -> dict:
        return {
            "mode": "elastic",
            "counts": {
                "traces": len(self.traces()),
                "decisions": len(self.decisions()),
            },
        }

    def _models(self, index_name: str, model_type: type[ModelT]) -> list[ModelT]:
        return [
            model_type.model_validate(record)
            for record in self.store.search_documents(index_name)
        ]
