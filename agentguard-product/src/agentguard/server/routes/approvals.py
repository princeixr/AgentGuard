"""Operator decision routes."""

from fastapi import APIRouter, Depends, HTTPException

from agentguard.server.dependencies import get_demo_runtime
from agentguard.server.models import ApprovalRecord, ApprovalRequest
from agentguard.server.services.live import DemoRuntimeService

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/{trace_id}", response_model=ApprovalRecord)
async def resolve_approval(
    trace_id: str,
    request: ApprovalRequest,
    runtime: DemoRuntimeService = Depends(get_demo_runtime),
) -> ApprovalRecord:
    try:
        return await runtime.resolve(trace_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
