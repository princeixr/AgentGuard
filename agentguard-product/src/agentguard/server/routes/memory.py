"""Decision memory routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from agentguard.server.dependencies import require_operator_access, get_query_service
from agentguard.server.models import MemoryDetail, MemoryPage
from agentguard.server.services.query import DashboardQueryService

router = APIRouter(prefix="/memory", tags=["memory"], dependencies=[Depends(require_operator_access)])


@router.get("", response_model=MemoryPage)
def list_memory(
    query: str | None = None,
    agent: str | None = None,
    tool: str | None = None,
    decision: str | None = None,
    risk_min: float | None = Query(default=None, ge=0.0, le=1.0),
    risk_max: float | None = Query(default=None, ge=0.0, le=1.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    service: DashboardQueryService = Depends(get_query_service),
) -> MemoryPage:
    return service.memory(
        query=query,
        agent=agent,
        tool=tool,
        decision=decision,
        risk_min=risk_min,
        risk_max=risk_max,
        page=page,
        page_size=page_size,
    )


@router.get("/{trace_id}", response_model=MemoryDetail)
def get_memory(
    trace_id: str,
    service: DashboardQueryService = Depends(get_query_service),
) -> MemoryDetail:
    result = service.memory_detail(trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found.")
    return result
