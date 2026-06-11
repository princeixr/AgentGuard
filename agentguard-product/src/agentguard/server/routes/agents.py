"""Demo agent registry routes."""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from agentguard.server.dependencies import require_operator_access, get_agent_registry
from agentguard.server.models import (
    AgentDefinition,
    AgentPolicyResponse,
    GuardAdminStatus,
    AgentListResponse,
    DemoSessionContext,
    PolicyUpdateRequest,
    PolicyValidationRequest,
    PolicyValidationResponse,
)
from agentguard.server.services.guard_admin import guard_admin_status
from agentguard.control_plane.models import AgentRecord, RegisteredAgentDefinition
from agentguard.control_plane.registry import AgentRegistry
from agentguard.firewall_v2.policy.models import PolicyDocumentV1
from agentguard.firewall_v2.policy.loader import LoadedPolicy
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy
from agentguard.firewall_v2.policy.store import PolicyConflictError, PolicyStore
from agentguard.firewall_v2.policy.validator import PolicyValidationError, validate_policy_scope
from agentguard.firewall_v2.tools.registry import descriptor_for_tool
from agentguard.firewall_v2.tools.metadata_inference import infer_registered_tool_metadata
from agentguard.server.models import AgentToolDefinition

router = APIRouter(tags=["agents"], dependencies=[Depends(require_operator_access)])


@router.get("/me", response_model=DemoSessionContext)
def current_demo_session(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> DemoSessionContext:
    return DemoSessionContext(user=registry.user, workspace=registry.workspace)


@router.get("/agents", response_model=AgentListResponse)
def list_agents(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentListResponse:
    return AgentListResponse(
        items=registry.list_agents(registry.workspace.workspace_id)
    )


@router.get("/agents/{agent_id}", response_model=AgentRecord)
def get_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentRecord:
    agent = registry.get_agent(registry.workspace.workspace_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent


@router.get("/agents/{agent_id}/definition", response_model=AgentDefinition)
def get_agent_definition(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentDefinition:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    definition = registry.definition(agent_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Agent definition not found.")
    return _definition_response(definition)


@router.get("/agents/{agent_id}/guard", response_model=GuardAdminStatus)
def get_guard_admin_status(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> GuardAdminStatus:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return guard_admin_status(agent_id, registry)


@router.get("/agents/{agent_id}/policy", response_model=AgentPolicyResponse)
def get_agent_policy(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentPolicyResponse:
    if registry.get_agent(registry.workspace.workspace_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return _policy_response(resolve_demo_policy())


@router.put("/agents/{agent_id}/policy", response_model=AgentPolicyResponse)
def update_agent_policy(
    agent_id: str,
    request: PolicyUpdateRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
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
    registry: AgentRegistry = Depends(get_agent_registry),
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

def _definition_response(definition: RegisteredAgentDefinition) -> AgentDefinition:
    tools = []
    for tool in definition.tools:
        descriptor = descriptor_for_tool(
            tool.name,
            infer_registered_tool_metadata(tool),
        )
        tools.append(
            AgentToolDefinition(
                name=tool.name,
                description=tool.description,
                category=descriptor.category,
                risk_level=descriptor.impact,
                side_effect_type=descriptor.side_effect,
                requires_confirmation=descriptor.impact in {"high", "unknown"},
                irreversible=descriptor.reversible is False,
                enabled=True,
                provider=tool.provider,
                domain=descriptor.domain,
                operation=descriptor.operation,
                capabilities=descriptor.capabilities,
                impact=descriptor.impact,
                reversible=descriptor.reversible,
                normalizer=descriptor.normalizer,
                metadata_status=descriptor.metadata_status,
                metadata_confidence=descriptor.metadata_confidence,
                metadata_provenance=[
                    *tool.metadata_provenance,
                    *descriptor.metadata_provenance,
                ],
                argument_roles=descriptor.argument_roles,
            )
        )
    return AgentDefinition(
        agent_id=definition.agent_id,
        deployment_id=definition.deployment_id,
        integration_id=definition.integration_id,
        framework=definition.framework,
        runtime_version=definition.runtime_version,
        environment=definition.environment,
        manifest_version=definition.manifest_version,
        system_instruction_hash=definition.system_instruction_hash,
        system_instruction_summary=definition.system_instruction_summary,
        agent_ui_url=definition.agent_ui_url,
        tools=tools,
    )
