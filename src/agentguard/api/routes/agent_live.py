"""Agent-scoped live interception routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse

from agentguard.api.dependencies import (
    get_agent_live_runtime,
    get_agent_registry,
    get_demo_runtime,
)
from agentguard.api.models import (
    ApprovalRecord,
    ApprovalRequest,
    CurrentInterception,
    DemoStartResponse,
)
from agentguard.api.services.live import DemoRuntimeService
from agentguard.api.services.agent_live import AgentLiveRuntimeService
from agentguard.control_plane.registry import DemoAgentRegistry

router = APIRouter(prefix="/agents/{agent_id}", tags=["agent live"])


def _require_agent(agent_id: str, registry: DemoAgentRegistry) -> None:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")


@router.get("/interceptions/current", response_model=CurrentInterception)
def current(
    agent_id: str,
    runtime: AgentLiveRuntimeService = Depends(get_agent_live_runtime),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> CurrentInterception:
    _require_agent(agent_id, registry)
    return runtime.current(agent_id)


@router.get("/events/stream")
async def events(
    agent_id: str,
    runtime: AgentLiveRuntimeService = Depends(get_agent_live_runtime),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
):
    _require_agent(agent_id, registry)

    async def generate():
        yield _format_sse(
            "state",
            runtime.current(agent_id).model_dump(mode="json"),
        )
        async for envelope in runtime.subscribe(agent_id):
            yield _format_sse(envelope.event, envelope.data)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/demo/scenarios/{scenario_id}/start",
    response_model=DemoStartResponse,
)
async def start(
    agent_id: str,
    scenario_id: str,
    runtime: DemoRuntimeService = Depends(get_demo_runtime),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> DemoStartResponse:
    _require_agent(agent_id, registry)
    try:
        return await runtime.start(scenario_id, agent_id=agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scenario not found.") from exc


@router.post("/approvals/{trace_id}", response_model=ApprovalRecord)
async def resolve(
    agent_id: str,
    trace_id: str,
    request: ApprovalRequest,
    runtime: AgentLiveRuntimeService = Depends(get_agent_live_runtime),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> ApprovalRecord:
    _require_agent(agent_id, registry)
    raise HTTPException(
        status_code=501,
        detail=(
            "Live ADK approval resume is not implemented. AgentGuard currently "
            "prevents the tool execution and records the intervention."
        ),
    )


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
