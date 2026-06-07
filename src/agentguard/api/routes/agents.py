"""Demo agent registry routes."""

from fastapi import APIRouter, Depends, HTTPException

from agentguard.api.dependencies import get_adk_test_service, get_agent_registry
from agentguard.api.models import (
    AgentDefinition,
    AgentListResponse,
    AgentTestRunRequest,
    AgentTestRunResponse,
    DemoSessionContext,
)
from agentguard.api.services.adk_test import ADKConfigurationError, GoogleADKTestService
from agentguard.control_plane.models import AgentRecord
from agentguard.control_plane.registry import DemoAgentRegistry

router = APIRouter(tags=["agents"])


@router.get("/me", response_model=DemoSessionContext)
def current_demo_session(
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> DemoSessionContext:
    return DemoSessionContext(user=registry.user, workspace=registry.workspace)


@router.get("/agents", response_model=AgentListResponse)
def list_agents(
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> AgentListResponse:
    return AgentListResponse(
        items=registry.list_agents(registry.workspace.workspace_id)
    )


@router.get("/agents/{agent_id}", response_model=AgentRecord)
def get_agent(
    agent_id: str,
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> AgentRecord:
    agent = registry.get_agent(registry.workspace.workspace_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent


@router.get("/agents/{agent_id}/definition", response_model=AgentDefinition)
def get_agent_definition(
    agent_id: str,
    registry: DemoAgentRegistry = Depends(get_agent_registry),
    service: GoogleADKTestService = Depends(get_adk_test_service),
) -> AgentDefinition:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return AgentDefinition.model_validate(service.definition())


@router.post("/agents/{agent_id}/test-runs", response_model=AgentTestRunResponse)
async def run_agent_test(
    agent_id: str,
    request: AgentTestRunRequest,
    registry: DemoAgentRegistry = Depends(get_agent_registry),
    service: GoogleADKTestService = Depends(get_adk_test_service),
) -> AgentTestRunResponse:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    try:
        return await service.run(request.message)
    except ADKConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Google ADK test run failed: {exc}",
        ) from exc
