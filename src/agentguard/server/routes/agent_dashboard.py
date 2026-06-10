"""Agent-scoped dashboard routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from agentguard.server.dependencies import get_agent_registry, get_query_service
from agentguard.server.models import (
    MemoryDetail,
    MemoryPage,
    OperationsSummary,
    SessionDetail,
    SessionSummary,
)
from agentguard.server.services.query import DashboardQueryService
from agentguard.server.routes.operations import build_export_response
from agentguard.control_plane.registry import DemoAgentRegistry

router = APIRouter(prefix="/agents/{agent_id}", tags=["agent dashboard"])


def _require_agent(agent_id: str, registry: DemoAgentRegistry) -> None:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")


@router.get("/sessions", response_model=list[SessionSummary])
def sessions(
    agent_id: str,
    service: DashboardQueryService = Depends(get_query_service),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> list[SessionSummary]:
    _require_agent(agent_id, registry)
    return service.sessions(agent_id=agent_id)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def session(
    agent_id: str,
    session_id: str,
    service: DashboardQueryService = Depends(get_query_service),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> SessionDetail:
    _require_agent(agent_id, registry)
    result = service.session(session_id, agent_id=agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return result


@router.get("/memory", response_model=MemoryPage)
def memory(
    agent_id: str,
    query: str | None = None,
    tool: str | None = None,
    decision: str | None = None,
    risk_min: float | None = Query(default=None, ge=0.0, le=1.0),
    risk_max: float | None = Query(default=None, ge=0.0, le=1.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    service: DashboardQueryService = Depends(get_query_service),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> MemoryPage:
    _require_agent(agent_id, registry)
    return service.memory(
        query=query,
        tool=tool,
        decision=decision,
        risk_min=risk_min,
        risk_max=risk_max,
        page=page,
        page_size=page_size,
        agent_id=agent_id,
    )


@router.get("/memory/{trace_id}", response_model=MemoryDetail)
def memory_detail(
    agent_id: str,
    trace_id: str,
    service: DashboardQueryService = Depends(get_query_service),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> MemoryDetail:
    _require_agent(agent_id, registry)
    result = service.memory_detail(trace_id, agent_id=agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found.")
    return result


@router.get("/operations/summary", response_model=OperationsSummary)
def operations(
    agent_id: str,
    service: DashboardQueryService = Depends(get_query_service),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> OperationsSummary:
    _require_agent(agent_id, registry)
    return service.operations(agent_id=agent_id)


@router.get("/operations/export")
def export_operations(
    agent_id: str,
    format: str = "csv",
    service: DashboardQueryService = Depends(get_query_service),
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> Response:
    _require_agent(agent_id, registry)
    records = service.memory(page_size=100, agent_id=agent_id).items
    return build_export_response(records, format)
