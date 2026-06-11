"""Response contracts for the AgentGuard product API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from agentguard.control_plane.models import AgentRecord, UserRecord, WorkspaceRecord

Decision = Literal["allow", "warn", "review", "require_approval", "block"]
RuntimeDecision = Literal["allow", "require_approval", "block"]


class ComponentHealth(BaseModel):
    name: str
    status: Literal["operational", "degraded", "unavailable"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["operational", "degraded"]
    mode: Literal["local", "elastic"]
    components: list[ComponentHealth]


class SessionSummary(BaseModel):
    session_id: str
    scenario_id: str | None = None
    agent_id: str
    agent_framework: str
    user_intent: str
    started_at: datetime
    updated_at: datetime
    step_count: int
    final_decision: Decision
    max_risk_score: float
    tool_sequence: list[str]


class GuardEvaluationView(BaseModel):
    firewall_mode: str
    firewall_version: str
    enforcement_status: str
    recommendation: Decision
    enforced_by: str
    explanation: str
    policy_id: str | None = None
    policy_version: str | None = None
    policy_hash: str | None = None
    matched_rules: list[dict[str, Any]] = Field(default_factory=list)
    deferred_rule_ids: list[str] = Field(default_factory=list)
    normalized_action: dict[str, Any] | None = None
    intent_contract: dict[str, Any] | None = None
    intent_authorization: dict[str, Any] | None = None
    evaluation_plan: dict[str, Any] | None = None
    tier_results: list[dict[str, Any]] = Field(default_factory=list)
    combined_decision: dict[str, Any] | None = None
    stages: list[dict[str, Any]] = Field(default_factory=list)


class ReplayStep(BaseModel):
    trace_id: str
    step_index: int
    timestamp: datetime
    tool_name: str
    tool_category: str
    arguments: dict[str, Any]
    argument_summary: str
    decision: Decision
    risk_score: float
    component_scores: dict[str, float]
    cumulative_risk: float
    dominant_signals: list[str]
    rules_fired: list[str]
    explanation: str
    execution_status: str
    output_summary: str | None = None
    guard_evaluation: GuardEvaluationView | None = None


class PrecedentSummary(BaseModel):
    trace_id: str
    session_id: str
    scenario_id: str | None = None
    tool_name: str
    decision: Decision
    risk_score: float
    intent: str


class SessionDetail(BaseModel):
    session: SessionSummary
    steps: list[ReplayStep]
    precedents: list[PrecedentSummary]


class MemoryItem(BaseModel):
    trace_id: str
    session_id: str
    timestamp: datetime
    agent_id: str
    agent_framework: str
    scenario_id: str | None = None
    domain: str
    tool_name: str
    tool_category: str
    risk_score: float
    decision: Decision
    labels: list[str]
    explanation: str
    guard_evaluation: GuardEvaluationView | None = None


class MemoryPage(BaseModel):
    items: list[MemoryItem]
    total: int
    page: int
    page_size: int


class MemoryDetail(BaseModel):
    item: MemoryItem
    trace: dict[str, Any]
    feature: dict[str, Any]
    score: dict[str, Any]
    decision: dict[str, Any]
    label: dict[str, Any] | None = None
    events: list[dict[str, Any]]
    precedents: list[PrecedentSummary]


class NamedMetric(BaseModel):
    name: str
    count: int
    rate: float = 0.0


class OperationsSummary(BaseModel):
    intercepted_calls: int
    intervention_count: int
    intervention_rate: float
    blocked_count: int
    blocked_rate: float
    session_count: int
    p50_latency_ms: int
    p95_latency_ms: int
    riskiest_tools: list[NamedMetric]
    failure_modes: list[NamedMetric]
    health: list[ComponentHealth]


class ApprovalRequest(BaseModel):
    action: Literal["approve", "reject", "abort"] | None = None
    actor: str = "operator"
    note: str | None = None


class ApprovalRecord(BaseModel):
    approval_id: str | None = None
    trace_id: str
    call_id: str | None = None
    action: Literal["approve", "reject", "abort"]
    actor: str
    note: str | None = None
    timestamp: datetime


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


class AgentRegistrationRequest(BaseModel):
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
    registered_at: datetime


class AgentRegistrationResponse(BaseModel):
    accepted: bool = True
    agent_id: str
    workspace_id: str


class TurnStartRequest(BaseModel):
    schema_version: Literal["agentguard.turn_start.v1"] = "agentguard.turn_start.v1"
    workspace_id: str
    agent_id: str
    deployment_id: str
    integration_id: str
    session_id: str
    turn_id: str
    user_request: str
    manifest_version: str
    timestamp: datetime


class TurnStartResponse(BaseModel):
    schema_version: Literal["agentguard.turn_start_result.v1"] = (
        "agentguard.turn_start_result.v1"
    )
    intent_id: str
    turn_id: str
    accepted: bool = True


class ToolProposalRequest(BaseModel):
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
    timestamp: datetime


class EnforcementDecisionResponse(BaseModel):
    schema_version: Literal["agentguard.enforcement_decision.v1"] = (
        "agentguard.enforcement_decision.v1"
    )
    decision_id: str
    trace_id: str
    call_id: str
    decision: RuntimeDecision
    explanation: str
    policy_id: str | None = None
    policy_version: str | None = None
    policy_hash: str | None = None
    matched_rules: list[dict[str, Any]] = Field(default_factory=list)
    normalized_action: dict[str, Any] | None = None
    tier_evidence: list[dict[str, Any]] = Field(default_factory=list)
    approval_request_id: str | None = None
    evaluation_latency_ms: int = 0


class OutcomeReportRequest(BaseModel):
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
    timestamp: datetime


class OutcomeReportResponse(BaseModel):
    accepted: bool = True


class GuardCheckRequest(BaseModel):
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
    timestamp: datetime | None = None


class GuardCheckResponse(BaseModel):
    schema_version: Literal["agentguard.guard_check_result.v2"] = (
        "agentguard.guard_check_result.v2"
    )
    allowed: bool
    requires_approval: bool
    decision: RuntimeDecision
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
    guard_evaluation: GuardEvaluationView | None = None
    status: Literal["pending", "approved", "rejected", "aborted", "expired"] = "pending"
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    note: str | None = None


class ApprovalListResponse(BaseModel):
    items: list[PendingApproval] = Field(default_factory=list)


class EventEnvelope(BaseModel):
    event: str
    data: dict[str, Any]


class CurrentInterception(BaseModel):
    status: Literal["idle", "running", "paused", "completed"]
    event_source: str = "registered_agent_runtime"
    firewall_mode: str = "v2"
    guard_version: str = "agentguard_firewall_v2"
    agent_id: str | None = None
    scenario_id: str | None = None
    session_id: str | None = None
    current_trace_id: str | None = None
    current_step: int = 0
    total_steps: int = 0
    approval: ApprovalRecord | None = None
    detail: MemoryDetail | None = None


class DemoStartResponse(BaseModel):
    scenario_id: str
    session_id: str
    status: Literal["running"]


class DemoResetResponse(BaseModel):
    destination: str
    status: Literal["reset"] = "reset"


class ScenarioSummary(BaseModel):
    scenario_id: str
    domain: str
    task_category: str
    user_request: str
    failure_type: str
    gold_final_verdict: str


class ScenarioList(BaseModel):
    items: list[ScenarioSummary] = Field(default_factory=list)


class AgentListResponse(BaseModel):
    items: list[AgentRecord] = Field(default_factory=list)


class DemoSessionContext(BaseModel):
    user: UserRecord
    workspace: WorkspaceRecord


class AgentToolDefinition(BaseModel):
    name: str
    description: str
    category: str
    risk_level: str
    side_effect_type: str | None = None
    requires_confirmation: bool
    irreversible: bool
    enabled: bool
    provider: str
    domain: str = "unknown"
    operation: str = "unknown"
    capabilities: list[str] = Field(default_factory=list)
    impact: str = "unknown"
    reversible: bool | None = None
    normalizer: str = "unsupported"
    metadata_status: str = "inferred"
    metadata_confidence: float = 0.0
    metadata_provenance: list[str] = Field(default_factory=list)
    argument_roles: dict[str, list[str]] = Field(default_factory=dict)


class AgentDefinition(BaseModel):
    agent_id: str
    deployment_id: str
    integration_id: str
    framework: str
    runtime_version: str
    environment: str
    manifest_version: str
    system_instruction_hash: str | None = None
    system_instruction_summary: str | None = None
    agent_ui_url: str | None = None
    tools: list[AgentToolDefinition]


class GuardAdminComponent(BaseModel):
    component_id: str
    name: str
    layer: str
    status: Literal[
        "operational",
        "observe_only",
        "disabled",
        "placeholder",
        "not_implemented",
    ]
    summary: str
    management: str


class GuardAdminPolicy(BaseModel):
    policy_id: str
    status: Literal["placeholder", "operational"]
    source: str
    editable: bool
    explanation: str
    version: str | None = None
    effective_hash: str | None = None
    rule_count: int = 0
    defaults: dict[str, Any] = Field(default_factory=dict)


class GuardAdminStatus(BaseModel):
    agent_id: str
    firewall_mode: str
    active_enforcement: str
    architecture_version: str
    force_block_enabled: bool
    approval_enforced: bool
    policy: GuardAdminPolicy
    components: list[GuardAdminComponent]
    tools: list[AgentToolDefinition]
    warnings: list[str] = Field(default_factory=list)


class AgentPolicyResponse(BaseModel):
    policy_id: str
    version: str
    status: str
    effective_hash: str
    source: str
    document: dict[str, Any]
    validation: Literal["valid"]


class PolicyValidationRequest(BaseModel):
    document: dict[str, Any]


class PolicyUpdateRequest(BaseModel):
    expected_hash: str = Field(min_length=8)
    document: dict[str, Any]


class PolicyValidationResponse(BaseModel):
    valid: bool
    policy_id: str | None = None
    version: str | None = None
    effective_hash: str | None = None
    errors: list[str] = Field(default_factory=list)
