"""Health routes."""

from fastapi import APIRouter, Depends

from agentguard.api.dependencies import get_query_service
from agentguard.api.models import HealthResponse
from agentguard.api.services.query import DashboardQueryService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(service: DashboardQueryService = Depends(get_query_service)) -> HealthResponse:
    return service.health()
