from __future__ import annotations

from agentguard.demo import generate_demo_fixtures, reset_demo_runtime
from agentguard.tracing.serializers import load_jsonl


def test_demo_fixture_generation_is_deterministic(tmp_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first_counts = generate_demo_fixtures(first_root)
    second_counts = generate_demo_fixtures(second_root)

    assert first_counts == second_counts
    assert first_counts == {
        "decisions": 13,
        "features": 13,
        "labels": 13,
        "live_events": 52,
        "scenarios": 4,
        "scores": 13,
        "session_risk": 4,
        "traces": 13,
    }
    for relative_path in [
        "traces.jsonl",
        "features.jsonl",
        "scores.jsonl",
        "decisions.jsonl",
        "live_events.jsonl",
        "labels.jsonl",
        "scenarios.jsonl",
        "manifest.json",
    ]:
        first = first_root / "v1" / "demo" / relative_path
        second = second_root / "v1" / "demo" / relative_path
        assert first.read_bytes() == second.read_bytes()


def test_demo_fixture_contains_expected_blocked_scenarios(tmp_path):
    generate_demo_fixtures(tmp_path)
    root = tmp_path / "v1" / "demo"
    traces = {record["trace_id"]: record for record in load_jsonl(root / "traces.jsonl")}
    decisions = load_jsonl(root / "decisions.jsonl")

    blocked = [decision for decision in decisions if decision["decision"] == "block"]
    blocked_scenarios = {
        traces[decision["trace_id"]]["source"]["scenario_id"] for decision in blocked
    }

    assert {"draft_vs_send", "file_scope_creep", "prompt_injection"} <= blocked_scenarios


def test_reset_demo_runtime_copies_fixture(tmp_path):
    fixture_root = tmp_path / "fixtures"
    runtime_root = tmp_path / "runtime"
    generate_demo_fixtures(fixture_root)

    destination = reset_demo_runtime(fixture_root, runtime_root)

    assert destination == runtime_root / "v1" / "demo"
    assert (destination / "manifest.json").exists()
    assert load_jsonl(destination / "traces.jsonl")
