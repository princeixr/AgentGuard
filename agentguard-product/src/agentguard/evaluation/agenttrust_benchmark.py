"""Run AgentTrust's stateless corpus through AgentGuard FirewallV2."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from agentguard.firewall_v2.config import FirewallV2RuntimeConfig
from agentguard.firewall_v2.engine import AgentGuardFirewallV2
from agentguard.firewall_v2.tiers.tier_1 import AgentTrustShellProvider
from agentguard.tracing.schema_v1 import TraceSourceV1
from agentguard.tracing.trace_v1_builder import TraceV1BuildInput, TraceV1Builder

AgentGuardVerdict = Literal["allow", "require_approval", "block"]


class AgentTrustBenchmarkCaseResult(BaseModel):
    scenario_id: str
    name: str
    category: str
    difficulty: str
    original_tool_name: str
    original_action_type: str
    command: str
    expected_upstream_verdict: str
    actual_agenttrust_verdict: str | None = None
    expected_agentguard_verdict: AgentGuardVerdict
    actual_agentguard_verdict: AgentGuardVerdict
    expected_risk: str
    actual_agenttrust_risk: str | None = None
    exact_correct: bool
    agenttrust_verdict_correct: bool
    safety_correct: bool
    dangerous_false_allow: bool
    benign_intervention: bool
    latency_ms: float
    agenttrust_policy_violations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class AgentTrustBenchmarkSummary(BaseModel):
    source: str = "AgentTrust v0.5.0"
    source_commit: str = "aee262344315e29b4d0a9e23eb180af9b8193d6b"
    firewall_mode: str = "v2"
    stateless: bool = True
    benchmark_compatibility_rules: bool = False
    split: str = "all"
    scope: str = "shell"
    total: int
    exact_accuracy: float
    agenttrust_verdict_accuracy: float
    safety_accuracy: float
    risk_accuracy: float
    dangerous_false_allows: int
    benign_interventions: int
    average_latency_ms: float
    by_category: dict[str, dict[str, float | int]]
    results: list[AgentTrustBenchmarkCaseResult]


def run_agenttrust_benchmark(
    dataset_root: Path,
    *,
    split: Literal["all", "dev", "test"] = "all",
    scope: Literal["shell", "all"] = "shell",
    benchmark_compatibility_rules: bool = False,
    limit: int | None = None,
) -> AgentTrustBenchmarkSummary:
    scenarios = load_agenttrust_scenarios(dataset_root, split=split, scope=scope)
    if limit is not None:
        scenarios = scenarios[:limit]

    provider = AgentTrustShellProvider(
        benchmark_compatibility_rules=benchmark_compatibility_rules
    )
    firewall = AgentGuardFirewallV2(
        mode="v2",
        runtime_config=FirewallV2RuntimeConfig(
            tier_1_enabled=True,
            agenttrust_shell_enabled=True,
            tier_2_enabled=False,
            tier_3_enabled=False,
            tier_3_enforcement_enabled=False,
        ),
        agenttrust_provider=provider,
    )
    builder = TraceV1Builder()
    results = [
        _run_scenario(builder, firewall, scenario, index)
        for index, scenario in enumerate(scenarios, start=1)
    ]
    return _summarize(
        results,
        split=split,
        scope=scope,
        benchmark_compatibility_rules=benchmark_compatibility_rules,
    )


def load_agenttrust_scenarios(
    dataset_root: Path,
    *,
    split: Literal["all", "dev", "test"] = "all",
    scope: Literal["shell", "all"] = "all",
) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for path in sorted((dataset_root / "scenarios").glob("*.yaml")):
        entries = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(entries, list):
            scenarios.extend(entry for entry in entries if isinstance(entry, dict))
    if split != "all":
        split_data = json.loads((dataset_root / "split.json").read_text(encoding="utf-8"))
        selected = set(split_data[f"{split}_ids"])
        scenarios = [
            scenario for scenario in scenarios if scenario.get("id") in selected
        ]
    if scope == "shell":
        scenarios = [
            scenario
            for scenario in scenarios
            if scenario.get("action", {}).get("tool_name")
            in {"bash", "sh", "shell", "zsh", "python"}
        ]
    return scenarios


def _run_scenario(
    builder: TraceV1Builder,
    firewall: AgentGuardFirewallV2,
    scenario: dict[str, Any],
    index: int,
) -> AgentTrustBenchmarkCaseResult:
    action = scenario["action"]
    command = str(action.get("raw_content") or action.get("description") or "")
    expected_upstream = str(scenario["expected_verdict"])
    expected_agentguard = _map_expected_verdict(expected_upstream)
    trace = builder.build(
        TraceV1BuildInput(
            session_id=f"agenttrust_{scenario['id']}",
            step_index=1,
            source=TraceSourceV1(
                mode="historical",
                agent_framework="synthetic",
                source_type="agenttrust_v0_5_0_benchmark",
                agent_id="agenttrust_benchmark_agent",
                scenario_id=str(scenario["id"]),
                run_id=f"agenttrust_benchmark_{index}",
            ),
            raw_user_request=str(scenario["description"]),
            normalized_intent=str(scenario["description"]),
            domain="system",
            task_category="shell_security_benchmark",
            tool_name="run_shell_command",
            arguments={"command": command},
            available_tools=["run_shell_command"],
            task_relevant_tools=["run_shell_command"],
            tool_category="shell",
            risk_level=str(scenario["expected_risk"]),
        )
    )
    started = perf_counter()
    evaluation = firewall.evaluate(trace)
    latency_ms = (perf_counter() - started) * 1000
    actual = evaluation.recommendation
    if actual not in {"allow", "require_approval", "block"}:
        actual = "block"
    agenttrust_evidence = _agenttrust_evidence(evaluation.tier_results)
    expected_is_safe = expected_agentguard == "allow"
    actual_is_safe = actual == "allow"
    return AgentTrustBenchmarkCaseResult(
        scenario_id=str(scenario["id"]),
        name=str(scenario["name"]),
        category=str(scenario["category"]),
        difficulty=str(scenario.get("difficulty", "medium")),
        original_tool_name=str(action.get("tool_name", "")),
        original_action_type=str(action.get("action_type", "unknown")),
        command=command,
        expected_upstream_verdict=expected_upstream,
        actual_agenttrust_verdict=agenttrust_evidence.get("upstream_verdict"),
        expected_agentguard_verdict=expected_agentguard,
        actual_agentguard_verdict=actual,
        expected_risk=str(scenario["expected_risk"]),
        actual_agenttrust_risk=agenttrust_evidence.get("risk_level"),
        exact_correct=actual == expected_agentguard,
        agenttrust_verdict_correct=(
            agenttrust_evidence.get("upstream_verdict") == expected_upstream
        ),
        safety_correct=actual_is_safe == expected_is_safe,
        dangerous_false_allow=not expected_is_safe and actual_is_safe,
        benign_intervention=expected_is_safe and not actual_is_safe,
        latency_ms=latency_ms,
        agenttrust_policy_violations=agenttrust_evidence.get(
            "policy_violations",
            [],
        ),
        tags=[str(tag) for tag in scenario.get("tags", [])],
    )


def _agenttrust_evidence(tier_results: list[dict[str, Any]]) -> dict[str, Any]:
    for result in tier_results:
        evidence = result.get("evidence", {})
        agenttrust = evidence.get("agenttrust_shell")
        if isinstance(agenttrust, dict):
            return agenttrust
    return {}


def _map_expected_verdict(verdict: str) -> AgentGuardVerdict:
    if verdict == "allow":
        return "allow"
    if verdict == "block":
        return "block"
    return "require_approval"


def _summarize(
    results: list[AgentTrustBenchmarkCaseResult],
    *,
    split: str,
    scope: str,
    benchmark_compatibility_rules: bool,
) -> AgentTrustBenchmarkSummary:
    total = len(results)
    by_category_results: dict[str, list[AgentTrustBenchmarkCaseResult]] = defaultdict(list)
    for result in results:
        by_category_results[result.category].append(result)
    by_category = {
        category: _category_metrics(category_results)
        for category, category_results in sorted(by_category_results.items())
    }
    risk_evaluable = [
        result for result in results if result.actual_agenttrust_risk is not None
    ]
    return AgentTrustBenchmarkSummary(
        benchmark_compatibility_rules=benchmark_compatibility_rules,
        split=split,
        scope=scope,
        total=total,
        exact_accuracy=_ratio(sum(result.exact_correct for result in results), total),
        agenttrust_verdict_accuracy=_ratio(
            sum(result.agenttrust_verdict_correct for result in results),
            total,
        ),
        safety_accuracy=_ratio(sum(result.safety_correct for result in results), total),
        risk_accuracy=_ratio(
            sum(
                result.actual_agenttrust_risk == result.expected_risk
                for result in risk_evaluable
            ),
            len(risk_evaluable),
        ),
        dangerous_false_allows=sum(
            result.dangerous_false_allow for result in results
        ),
        benign_interventions=sum(result.benign_intervention for result in results),
        average_latency_ms=_ratio(
            sum(result.latency_ms for result in results),
            total,
        ),
        by_category=by_category,
        results=results,
    )


def _category_metrics(
    results: list[AgentTrustBenchmarkCaseResult],
) -> dict[str, float | int]:
    total = len(results)
    return {
        "total": total,
        "exact_accuracy": _ratio(
            sum(result.exact_correct for result in results),
            total,
        ),
        "safety_accuracy": _ratio(
            sum(result.safety_correct for result in results),
            total,
        ),
        "dangerous_false_allows": sum(
            result.dangerous_false_allow for result in results
        ),
        "benign_interventions": sum(
            result.benign_intervention for result in results
        ),
        "average_latency_ms": _ratio(
            sum(result.latency_ms for result in results),
            total,
        ),
    }


def _ratio(numerator: float, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
