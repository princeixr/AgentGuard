from __future__ import annotations

from fastapi.testclient import TestClient

from agentguard.server.app import create_app
from agentguard.demo import generate_demo_fixtures


def _client(tmp_path) -> TestClient:
    fixture_root = tmp_path / "fixtures"
    generate_demo_fixtures(fixture_root)
    return TestClient(
        create_app(
            data_root=tmp_path / "runtime",
            fixture_root=fixture_root,
        )
    )


def test_health_and_scenarios(tmp_path):
    client = _client(tmp_path)

    health = client.get("/api/v1/health")
    scenarios = client.get("/api/v1/demo/scenarios")

    assert health.status_code == 200
    assert health.json()["status"] == "operational"
    assert health.json()["mode"] == "local"
    assert scenarios.status_code == 200
    assert len(scenarios.json()["items"]) == 4


def test_sessions_and_replay_are_joined(tmp_path):
    client = _client(tmp_path)

    sessions = client.get("/api/v1/sessions").json()
    draft_vs_send = next(
        item for item in sessions if item["session_id"] == "demo_draft_vs_send"
    )
    replay = client.get("/api/v1/sessions/demo_draft_vs_send")

    assert len(sessions) == 4
    assert draft_vs_send["final_decision"] == "block"
    assert draft_vs_send["step_count"] == 4
    assert replay.status_code == 200
    assert replay.json()["steps"][-1]["tool_name"] == "gmail_send"
    assert replay.json()["steps"][-1]["execution_status"] == "blocked"
    assert replay.json()["steps"][-1]["rules_fired"] == [
        "tool_in_intent_forbidden_set"
    ]


def test_memory_filters_pagination_and_detail(tmp_path):
    client = _client(tmp_path)

    blocked = client.get(
        "/api/v1/memory",
        params={"decision": "block", "page_size": 2},
    ).json()
    searched = client.get("/api/v1/memory", params={"query": "prompt injection"}).json()
    detail = client.get(f"/api/v1/memory/{blocked['items'][0]['trace_id']}")

    assert blocked["total"] == 3
    assert len(blocked["items"]) == 2
    assert all(item["decision"] == "block" for item in blocked["items"])
    assert searched["total"] >= 1
    assert detail.status_code == 200
    assert detail.json()["trace"]["trace_id"] == blocked["items"][0]["trace_id"]
    assert detail.json()["events"]


def test_operations_metrics_reconcile_with_fixture(tmp_path):
    client = _client(tmp_path)

    summary = client.get("/api/v1/operations/summary")

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["intercepted_calls"] == 13
    assert payload["blocked_count"] == 3
    assert payload["session_count"] == 4
    assert payload["blocked_rate"] == 3 / 13
    assert {item["name"] for item in payload["failure_modes"]} == {
        "premature_irreversible_action",
        "scope_creep",
        "prompt_injection_from_tool_output",
    }


def test_operations_export_supports_csv_and_jsonl(tmp_path):
    client = _client(tmp_path)

    csv_response = client.get("/api/v1/operations/export")
    jsonl_response = client.get(
        "/api/v1/operations/export",
        params={"format": "jsonl"},
    )

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "trace_id,session_id" in csv_response.text
    assert jsonl_response.status_code == 200
    assert len(jsonl_response.text.strip().splitlines()) == 13


def test_missing_records_return_404(tmp_path):
    client = _client(tmp_path)

    assert client.get("/api/v1/sessions/missing").status_code == 404
    assert client.get("/api/v1/memory/missing").status_code == 404


def test_elastic_startup_failure_falls_back_to_local(
    monkeypatch,
    tmp_path,
):
    fixture_root = tmp_path / "fixtures"
    generate_demo_fixtures(fixture_root)
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "true")
    monkeypatch.setenv("ELASTICSEARCH_URL", "http://elastic.test")
    monkeypatch.setenv("ELASTICSEARCH_API_KEY", "test")

    def fail_elastic(_self):
        raise RuntimeError("test Elastic outage")

    monkeypatch.setattr(
        "agentguard.server.app.ElasticDashboardRepository.is_ready",
        fail_elastic,
    )
    client = TestClient(
        create_app(
            data_root=tmp_path / "runtime",
            fixture_root=fixture_root,
        )
    )

    health = client.get("/api/v1/health").json()

    assert health["status"] == "operational"
    assert health["mode"] == "local"
    elastic = next(
        component
        for component in health["components"]
        if component["name"] == "Elastic Search"
    )
    assert "test Elastic outage" in elastic["detail"]
