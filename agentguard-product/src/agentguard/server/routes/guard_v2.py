"""One-call AgentGuard API for simple integrations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from agentguard.server.dependencies import get_remote_runtime, require_api_key
from agentguard.server.models import (
    AgentRegistrationRequest,
    GuardCheckRequest,
    GuardCheckResponse,
    ToolProposalRequest,
    TurnStartRequest,
)
from agentguard.server.services.remote_runtime import RemoteInterceptionService
from agentguard.tool_registry import infer_tool_metadata, manifest_from_tool

router = APIRouter(tags=["guard v2"], dependencies=[Depends(require_api_key)])


@router.post("/guard/check", response_model=GuardCheckResponse)
async def guard_check(
    request: GuardCheckRequest,
    runtime: RemoteInterceptionService = Depends(get_remote_runtime),
) -> GuardCheckResponse:
    timestamp = request.timestamp or datetime.now(timezone.utc)
    session_id = request.session_id or f"sess_{uuid4().hex}"
    turn_id = request.turn_id or f"turn_{uuid4().hex}"
    call_id = request.call_id or f"call_{uuid4().hex}"
    tool_metadata = infer_tool_metadata(
        name=request.tool_name,
        tool_type=request.tool_type,
        overrides=request.metadata_overrides,
    )
    tool_manifest = manifest_from_tool(
        name=request.tool_name,
        tool_type=request.tool_type,
        description=request.tool_description,
        input_schema=request.tool_input_schema,
        framework=request.framework,
        overrides=request.metadata_overrides,
    )
    _ensure_registered(runtime, request, tool_manifest, timestamp)
    try:
        turn = await runtime.start_turn(
            TurnStartRequest(
                workspace_id=request.workspace_id,
                agent_id=request.agent_id,
                deployment_id=request.deployment_id,
                integration_id=request.integration_id,
                session_id=session_id,
                turn_id=turn_id,
                user_request=request.user_message,
                manifest_version=request.manifest_version,
                timestamp=timestamp,
            )
        )
        decision = await runtime.evaluate(
            ToolProposalRequest(
                workspace_id=request.workspace_id,
                agent_id=request.agent_id,
                deployment_id=request.deployment_id,
                integration_id=request.integration_id,
                session_id=session_id,
                turn_id=turn_id,
                intent_id=turn.intent_id,
                call_id=call_id,
                tool_name=request.tool_name,
                arguments=request.arguments,
                timestamp=timestamp,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown agent or tool: {exc}") from exc

    return GuardCheckResponse(
        allowed=decision.decision == "allow",
        requires_approval=decision.decision == "require_approval",
        decision=decision.decision,
        reason=decision.explanation,
        agent_id=request.agent_id,
        session_id=session_id,
        turn_id=turn_id,
        call_id=call_id,
        tool_name=request.tool_name,
        tool_type=tool_metadata.tool_type,
        trace_id=decision.trace_id,
        decision_id=decision.decision_id,
        approval_id=decision.approval_request_id,
        risk_level=tool_metadata.risk_level,
        matched_rules=decision.matched_rules,
        normalized_action=decision.normalized_action,
        tier_evidence=decision.tier_evidence,
    )


def _ensure_registered(
    runtime: RemoteInterceptionService,
    request: GuardCheckRequest,
    tool_manifest,
    timestamp: datetime,
) -> None:
    definition = runtime.registry.definition(request.agent_id)
    tools = list(definition.tools) if definition is not None else []
    if not any(tool.name == request.tool_name for tool in tools):
        tools.append(tool_manifest)
    runtime.register(
        AgentRegistrationRequest(
            workspace_id=request.workspace_id,
            agent_id=request.agent_id,
            deployment_id=request.deployment_id,
            integration_id=request.integration_id,
            name=request.agent_id,
            description=f"Auto-registered AgentGuard integration for {request.agent_id}.",
            framework=request.framework,
            runtime_version=request.runtime_version,
            environment=request.environment,
            manifest_version=request.manifest_version,
            tools=tools,
            registered_at=timestamp,
        )
    )
