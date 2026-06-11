"""Versioned framework-neutral AgentGuard integration contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolManifest(BaseModel):
    schema_version: Literal["agentguard.tool_manifest.v1"] = "agentguard.tool_manifest.v1"
    name: str
    source_name: str
    provider: str
    framework: str
    transport: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    metadata_provenance: list[str] = Field(default_factory=list)


class AgentRegistration(BaseModel):
    schema_version: Literal["agentguard.agent_registration.v1"] = (
        "agentguard.agent_registration.v1"
    )
    workspace_id: str
    agent_id: str
    deployment_id: str
    integration_id: str
    name: str
    description: str
    framework: str
    runtime_version: str
    environment: str
    system_instruction_hash: str | None = None
    system_instruction_summary: str | None = None
    manifest_version: str
    tools: list[ToolManifest]
    agent_ui_url: str | None = None
    registered_at: datetime = Field(default_factory=_utc_now)


class TurnStart(BaseModel):
    schema_version: Literal["agentguard.turn_start.v1"] = "agentguard.turn_start.v1"
    workspace_id: str
    agent_id: str
    deployment_id: str
    integration_id: str
    session_id: str
    turn_id: str
    user_request: str
    manifest_version: str
    timestamp: datetime = Field(default_factory=_utc_now)


class TurnStartResult(BaseModel):
    schema_version: Literal["agentguard.turn_start_result.v1"] = (
        "agentguard.turn_start_result.v1"
    )
    intent_id: str
    turn_id: str
    accepted: bool = True


class ToolProposal(BaseModel):
    schema_version: Literal["agentguard.tool_proposal.v1"] = "agentguard.tool_proposal.v1"
    workspace_id: str
    agent_id: str
    deployment_id: str
    integration_id: str
    session_id: str
    turn_id: str
    intent_id: str
    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    trajectory_cursor: str | None = None
    timestamp: datetime = Field(default_factory=_utc_now)


class EnforcementDecision(BaseModel):
    schema_version: Literal["agentguard.enforcement_decision.v1"] = (
        "agentguard.enforcement_decision.v1"
    )
    decision_id: str = Field(default_factory=lambda: f"dec_{uuid4().hex}")
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex}")
    call_id: str
    decision: Literal["allow", "require_approval", "block"]
    explanation: str
    policy_id: str | None = None
    policy_version: str | None = None
    policy_hash: str | None = None
    matched_rules: list[dict[str, Any]] = Field(default_factory=list)
    normalized_action: dict[str, Any] | None = None
    tier_evidence: list[dict[str, Any]] = Field(default_factory=list)
    approval_request_id: str | None = None
    evaluation_latency_ms: int = 0


class PendingApproval(BaseModel):
    approval_id: str
    decision_id: str
    trace_id: str
    call_id: str
    workspace_id: str
    agent_id: str
    deployment_id: str
    integration_id: str
    session_id: str
    turn_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    user_request: str
    explanation: str
    guard_evaluation: dict[str, Any] | None = None
    status: Literal["pending", "approved", "rejected", "aborted", "expired"] = "pending"
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    note: str | None = None


class OutcomeReport(BaseModel):
    schema_version: Literal["agentguard.outcome_report.v1"] = (
        "agentguard.outcome_report.v1"
    )
    decision_id: str
    call_id: str
    status: Literal["executed", "blocked", "failed", "cancelled"]
    output_summary: str | None = None
    latency_ms: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    timestamp: datetime = Field(default_factory=_utc_now)


class GuardCheck(BaseModel):
    schema_version: Literal["agentguard.guard_check.v2"] = "agentguard.guard_check.v2"
    workspace_id: str = "default"
    agent_id: str
    deployment_id: str = "default"
    integration_id: str = "default"
    session_id: str | None = None
    turn_id: str | None = None
    call_id: str | None = None
    user_message: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    tool_type: str | None = None
    tool_description: str | None = None
    tool_input_schema: dict[str, Any] | None = None
    framework: str = "custom"
    runtime_version: str = "unknown"
    environment: str = "production"
    manifest_version: str = "v2"
    metadata_overrides: dict[str, Any] = Field(default_factory=dict)
    approval_mode: Literal["none", "async", "wait"] = "async"
    timestamp: datetime = Field(default_factory=_utc_now)


class GuardCheckResult(BaseModel):
    schema_version: Literal["agentguard.guard_check_result.v2"] = (
        "agentguard.guard_check_result.v2"
    )
    allowed: bool
    requires_approval: bool
    decision: Literal["allow", "require_approval", "block"]
    reason: str
    agent_id: str
    session_id: str
    turn_id: str
    call_id: str
    tool_name: str
    tool_type: str
    trace_id: str
    decision_id: str
    approval_id: str | None = None
    risk_level: str | None = None
    matched_rules: list[dict[str, Any]] = Field(default_factory=list)
    normalized_action: dict[str, Any] | None = None
    tier_evidence: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.decision == "block"
