"""Session and replay routes."""

from fastapi import APIRouter, Depends, HTTPException

from agentguard.server.dependencies import get_query_service
from agentguard.server.models import SessionDetail, SessionSummary
from agentguard.server.services.query import DashboardQueryService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionSummary])
def list_sessions(
    service: DashboardQueryService = Depends(get_query_service),
) -> list[SessionSummary]:
    return service.sessions()


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    service: DashboardQueryService = Depends(get_query_service),
) -> SessionDetail:
    result = service.session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return result
