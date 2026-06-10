"""Merge canonical records from multiple runtime repositories."""

from __future__ import annotations

from agentguard.server.repositories.base import DashboardRepository


class MergedDashboardRepository:
    mode = "local"

    def __init__(self, repositories: list[DashboardRepository]):
        self.repositories = repositories
        self.fallback_reason = None

    @property
    def namespace_root(self):
        return [
            getattr(repository, "namespace_root", None)
            for repository in self.repositories
        ]

    def is_ready(self) -> bool:
        return any(repository.is_ready() for repository in self.repositories)

    def traces(self):
        return self._merge("traces", "trace_id")

    def features(self):
        return self._merge("features", "feature_id")

    def scores(self):
        return self._merge("scores", "score_id")

    def decisions(self):
        return self._merge("decisions", "decision_id")

    def live_events(self):
        return self._merge("live_events", "event_id")

    def labels(self):
        return self._merge("labels", "label_id")

    def scenarios(self):
        return self._merge("scenarios", "scenario_id")

    def session_states(self):
        return self._merge("session_states", "session_id")

    def manifest(self) -> dict:
        return {
            "mode": "merged_runtime",
            "sources": [
                repository.manifest() for repository in self.repositories
            ],
        }

    def _merge(self, method_name: str, identity_field: str):
        records = {}
        for repository in self.repositories:
            for record in getattr(repository, method_name)():
                records[getattr(record, identity_field)] = record
        return list(records.values())
