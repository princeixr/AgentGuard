"""Demo scenario metadata routes."""

from fastapi import APIRouter, Depends

from agentguard.api.dependencies import get_query_service
from agentguard.api.models import ScenarioList
from agentguard.api.services.query import DashboardQueryService

router = APIRouter(prefix="/demo/scenarios", tags=["demo"])


@router.get("", response_model=ScenarioList)
def scenarios(
    service: DashboardQueryService = Depends(get_query_service),
) -> ScenarioList:
    return service.scenarios()
