"""Dashboard repository that prefers live agent records over demo fixtures."""

from __future__ import annotations

from agentguard.api.repositories.base import DashboardRepository


class RuntimeFirstDashboardRepository:
    mode = "local"

    def __init__(
        self,
        runtime: DashboardRepository,
        fallback: DashboardRepository,
    ):
        self.runtime = runtime
        self.fallback = fallback
        self.fallback_reason = None

    @property
    def namespace_root(self):
        return getattr(self.runtime, "namespace_root", None)

    def is_ready(self) -> bool:
        return self.runtime.is_ready() or self.fallback.is_ready()

    def traces(self):
        return self._runtime_or_fallback("traces")

    def features(self):
        return self._runtime_or_fallback("features")

    def scores(self):
        return self._runtime_or_fallback("scores")

    def decisions(self):
        return self._runtime_or_fallback("decisions")

    def live_events(self):
        return self._runtime_or_fallback("live_events")

    def labels(self):
        if self.runtime.traces():
            return self.runtime.labels()
        return self.fallback.labels()

    def scenarios(self):
        return self.fallback.scenarios()

    def session_states(self):
        return self._runtime_or_fallback("session_states")

    def manifest(self) -> dict:
        using_runtime = bool(self.runtime.traces())
        return {
            "mode": "runtime" if using_runtime else "demo_fallback",
            "runtime": self.runtime.manifest(),
            "fallback": self.fallback.manifest(),
        }

    def _runtime_or_fallback(self, method_name: str):
        if self.runtime.traces():
            return getattr(self.runtime, method_name)()
        return getattr(self.fallback, method_name)()
