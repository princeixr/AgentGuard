"""Deterministic demo controls."""

from fastapi import APIRouter, Depends, HTTPException, Request

from agentguard.api.dependencies import get_demo_runtime
from agentguard.api.models import DemoResetResponse, DemoStartResponse
from agentguard.api.services.live import DemoRuntimeService
from agentguard.demo import reset_demo_runtime

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/scenarios/{scenario_id}/start", response_model=DemoStartResponse)
async def start_scenario(
    scenario_id: str,
    runtime: DemoRuntimeService = Depends(get_demo_runtime),
) -> DemoStartResponse:
    try:
        return await runtime.start(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scenario not found.") from exc


@router.post("/reset", response_model=DemoResetResponse)
async def reset_demo(
    request: Request,
    runtime: DemoRuntimeService = Depends(get_demo_runtime),
) -> DemoResetResponse:
    await runtime.reset()
    destination = reset_demo_runtime(
        request.app.state.fixture_root,
        request.app.state.data_root,
    )
    return DemoResetResponse(destination=str(destination))
