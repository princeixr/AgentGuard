"""Scenario loading and benchmark orchestration."""

from __future__ import annotations

from pathlib import Path

from agentguard.core.models import ScenarioRecord
from agentguard.tracing.serializers import load_jsonl


def load_scenarios(path: str | Path) -> list[ScenarioRecord]:
    return [ScenarioRecord.model_validate(record) for record in load_jsonl(Path(path))]


class BenchmarkRunner:
    def __init__(self, runtime_adapter, guard_registry=None, trace_store=None):
        self.runtime_adapter = runtime_adapter
        self.guard_registry = guard_registry or {}
        self.trace_store = trace_store

    def run(self, scenario_file: str, guard_name: str = "full_agentguard") -> dict:
        scenarios = load_scenarios(scenario_file)
        traces = []
        for scenario in scenarios:
            traces.extend(self.runtime_adapter.run_session(scenario.scenario_id))
        return {
            "guard_name": guard_name,
            "scenario_count": len(scenarios),
            "trace_count": len(traces),
        }

