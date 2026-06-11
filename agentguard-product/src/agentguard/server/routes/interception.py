"""Production remote interception API."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import StreamingResponse

from agentguard.server.dependencies import get_remote_runtime, require_api_key
from agentguard.server.models import (
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    ApprovalListResponse,
    ApprovalRequest,
    EnforcementDecisionResponse,
    OutcomeReportRequest,
    OutcomeReportResponse,
    PendingApproval,
    ToolProposalRequest,
    TurnStartRequest,
    TurnStartResponse,
)
from agentguard.server.services.remote_runtime import RemoteInterceptionService

router = APIRouter(tags=["remote interception"], dependencies=[Depends(require_api_key)])


@router.post("/agents/register", response_model=AgentRegistrationResponse)
def register_agent(
    request: AgentRegistrationRequest,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> AgentRegistrationResponse:
    return runtime.register(request)


@router.post("/turns/start", response_model=TurnStartResponse)
async def start_turn(
    request: TurnStartRequest,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> TurnStartResponse:
    try:
        return await runtime.start_turn(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Agent not registered: {exc}") from exc


@router.post("/tool-proposals/evaluate", response_model=EnforcementDecisionResponse)
async def evaluate_tool_proposal(
    request: ToolProposalRequest,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> EnforcementDecisionResponse:
    try:
        return await runtime.evaluate(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown agent or tool: {exc}") from exc


@router.post("/tool-outcomes", response_model=OutcomeReportResponse)
async def report_tool_outcome(
    request: OutcomeReportRequest,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> OutcomeReportResponse:
    return await runtime.report_outcome(request)


@router.get("/approvals", response_model=ApprovalListResponse)
def list_approvals(
    status: str | None = Query(default="pending"),
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> ApprovalListResponse:
    return runtime.list_approvals(status=None if status == "all" else status)


@router.get("/approvals/{approval_id}", response_model=PendingApproval)
def get_approval(
    approval_id: str,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> PendingApproval:
    try:
        return runtime.get_approval(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found.") from exc


@router.post("/approvals/{approval_id}/approve", response_model=PendingApproval)
async def approve_tool_call(
    approval_id: str,
    request: ApprovalRequest,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> PendingApproval:
    try:
        return await runtime.resolve_approval(approval_id, request, "approve")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found.") from exc


@router.post("/approvals/{approval_id}/reject", response_model=PendingApproval)
async def reject_tool_call(
    approval_id: str,
    request: ApprovalRequest,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> PendingApproval:
    try:
        return await runtime.resolve_approval(approval_id, request, "reject")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found.") from exc


@router.get("/events/stream")
async def event_stream(
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
):
    async def generate():
        async for envelope in runtime.broker.subscribe():
            yield (
                f"event: {envelope.event}\n"
                f"data: {json.dumps(envelope.data, separators=(',', ':'))}\n\n"
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
