"""Demo agent registry routes."""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from agentguard.api.dependencies import get_adk_test_service, get_agent_registry
from agentguard.api.models import (
    AgentDefinition,
    AgentPolicyResponse,
    GuardAdminStatus,
    AgentListResponse,
    AgentTestRunRequest,
    AgentTestRunResponse,
    DemoSessionContext,
    PolicyUpdateRequest,
    PolicyValidationRequest,
    PolicyValidationResponse,
)
from agentguard.api.services.adk_test import ADKConfigurationError, GoogleADKTestService
from agentguard.api.services.guard_admin import guard_admin_status
from agentguard.control_plane.models import AgentRecord
from agentguard.control_plane.registry import DemoAgentRegistry
from agentguard.firewall_v2.policy.models import PolicyDocumentV1
from agentguard.firewall_v2.policy.loader import LoadedPolicy
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy
from agentguard.firewall_v2.policy.store import PolicyConflictError, PolicyStore
from agentguard.firewall_v2.policy.validator import PolicyValidationError, validate_policy_scope

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


@router.get("/agents/{agent_id}/guard", response_model=GuardAdminStatus)
def get_guard_admin_status(
    agent_id: str,
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> GuardAdminStatus:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return guard_admin_status(agent_id)


@router.get("/agents/{agent_id}/policy", response_model=AgentPolicyResponse)
def get_agent_policy(
    agent_id: str,
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> AgentPolicyResponse:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return _policy_response(resolve_demo_policy())


@router.put("/agents/{agent_id}/policy", response_model=AgentPolicyResponse)
def update_agent_policy(
    agent_id: str,
    request: PolicyUpdateRequest,
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> AgentPolicyResponse:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    try:
        loaded = PolicyStore().publish(
            request.document,
            expected_hash=request.expected_hash,
        )
    except PolicyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PolicyValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _policy_response(loaded)


def _policy_response(loaded: LoadedPolicy) -> AgentPolicyResponse:
    return AgentPolicyResponse(
        policy_id=loaded.document.policy_id,
        version=loaded.document.version,
        status=loaded.document.status,
        effective_hash=loaded.effective_hash,
        source=str(loaded.path),
        document=loaded.document.model_dump(mode="json"),
        validation="valid",
    )


@router.post(
    "/agents/{agent_id}/policy/validate",
    response_model=PolicyValidationResponse,
)
def validate_agent_policy(
    agent_id: str,
    request: PolicyValidationRequest,
    registry: DemoAgentRegistry = Depends(get_agent_registry),
) -> PolicyValidationResponse:
    agent = registry.get_agent(registry.workspace.workspace_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    try:
        active = resolve_demo_policy()
        policy = PolicyDocumentV1.model_validate(request.document)
        validate_policy_scope(
            policy,
            workspace_id=registry.workspace.workspace_id,
            agent_id=agent_id,
            deployment_id=agent.deployments[0].deployment_id,
        )
        if policy.policy_id != active.document.policy_id:
            raise PolicyValidationError("The assigned policy ID cannot be changed.")
    except (ValidationError, PolicyValidationError, ValueError) as exc:
        return PolicyValidationResponse(valid=False, errors=[str(exc)])
    canonical = json.dumps(
        policy.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return PolicyValidationResponse(
        valid=True,
        policy_id=policy.policy_id,
        version=policy.version,
        effective_hash=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )


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
