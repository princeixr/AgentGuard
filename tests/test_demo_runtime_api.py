from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from agentguard.server.app import create_app
from agentguard.server.models import ApprovalRequest
from agentguard.demo import generate_demo_fixtures


def _app(tmp_path):
    fixture_root = tmp_path / "fixtures"
    generate_demo_fixtures(fixture_root)
    app = create_app(data_root=tmp_path / "runtime", fixture_root=fixture_root)
    app.state.demo_runtime.step_delay_seconds = 0.001
    return app


def test_demo_start_pauses_on_blocked_interception_and_resolves(tmp_path):
    app = _app(tmp_path)

    async def exercise():
        runtime = app.state.demo_runtime
        started = await runtime.start("draft_vs_send")
        for _ in range(100):
            if runtime.current().status == "paused":
                break
            await asyncio.sleep(0.002)
        current = runtime.current()
        approval = await runtime.resolve(
            current.current_trace_id,
            ApprovalRequest(action="reject", note="User requested draft only."),
        )
        return started, current, approval, runtime.current()

    started, paused, approval, completed = asyncio.run(exercise())

    assert started.session_id == "demo_draft_vs_send"
    assert paused.status == "paused"
    assert paused.current_step == 4
    assert paused.detail.item.tool_name == "gmail_send"
    assert paused.detail.item.decision == "block"
    assert approval.action == "reject"
    assert completed.status == "completed"


def test_clean_demo_completes_without_pause(tmp_path):
    app = _app(tmp_path)

    async def exercise():
        runtime = app.state.demo_runtime
        await runtime.start("clean_email_draft")
        for _ in range(100):
            if runtime.current().status == "completed":
                break
            await asyncio.sleep(0.002)
        return runtime.current()

    completed = asyncio.run(exercise())

    assert completed.status == "completed"
    assert completed.current_step == 3
    assert completed.approval is None


def test_demo_control_endpoints_and_conflict(tmp_path):
    app = _app(tmp_path)
    client = TestClient(app)

    assert client.get("/api/v1/interceptions/current").json()["status"] == "idle"
    assert client.post("/api/v1/demo/scenarios/missing/start").status_code == 404
    conflict = client.post(
        "/api/v1/approvals/not-paused",
        json={"action": "approve"},
    )
    reset = client.post("/api/v1/demo/reset")

    assert conflict.status_code == 409
    assert reset.status_code == 200
    assert reset.json()["status"] == "reset"


def test_event_broker_delivers_published_envelope(tmp_path):
    app = _app(tmp_path)

    async def exercise():
        runtime = app.state.demo_runtime
        subscription = runtime.broker.subscribe()
        pending = asyncio.create_task(anext(subscription))
        await asyncio.sleep(0)
        await runtime.start("clean_email_draft")
        event = await asyncio.wait_for(pending, timeout=1)
        await subscription.aclose()
        await runtime.reset()
        return event

    event = asyncio.run(exercise())

    assert event.event == "scenario_started"
    assert event.data["scenario_id"] == "clean_email_draft"


@pytest.mark.parametrize("action", ["approve", "reject", "abort"])
def test_approval_request_actions_validate(action):
    assert ApprovalRequest(action=action).action == action
