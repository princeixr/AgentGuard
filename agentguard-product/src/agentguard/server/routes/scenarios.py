"""Demo scenario metadata routes."""

from fastapi import APIRouter, Depends

from agentguard.server.dependencies import require_operator_access, get_query_service
from agentguard.server.models import ScenarioList
from agentguard.server.services.query import DashboardQueryService

router = APIRouter(prefix="/demo/scenarios", tags=["demo"], dependencies=[Depends(require_operator_access)])


@router.get("", response_model=ScenarioList)
def scenarios(
    service: DashboardQueryService = Depends(get_query_service),
) -> ScenarioList:
    return service.scenarios()
