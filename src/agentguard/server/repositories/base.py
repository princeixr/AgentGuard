"""Repository contract for dashboard query services."""

from __future__ import annotations

from typing import Protocol

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


class DashboardRepository(Protocol):
    mode: str

    def is_ready(self) -> bool: ...

    def traces(self) -> list[AgentGuardTraceV1]: ...

    def features(self) -> list[TraceFeatureV1]: ...

    def scores(self) -> list[GuardScoreV1]: ...

    def decisions(self) -> list[GuardDecisionV1]: ...

    def live_events(self) -> list[LiveEventV1]: ...

    def labels(self) -> list[LabelRecordV1]: ...

    def scenarios(self) -> list[ScenarioRecordV1]: ...

    def session_states(self) -> list[SessionRiskStateV1]: ...

    def manifest(self) -> dict: ...
