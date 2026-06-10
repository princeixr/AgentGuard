"""Response contracts for the AgentGuard product API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from agentguard.control_plane.models import AgentRecord, UserRecord, WorkspaceRecord

Decision = Literal["allow", "warn", "review", "require_approval", "block"]


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
    action: Literal["approve", "reject", "abort"]
    actor: str = "demo_operator"
    note: str | None = None


class ApprovalRecord(BaseModel):
    trace_id: str
    action: Literal["approve", "reject", "abort"]
    actor: str
    note: str | None = None
    timestamp: datetime


class EventEnvelope(BaseModel):
    event: str
    data: dict[str, Any]


class CurrentInterception(BaseModel):
    status: Literal["idle", "running", "paused", "completed"]
    event_source: str = "google_adk_runtime"
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


class AgentTestScenario(BaseModel):
    id: str
    name: str
    prompt: str
    expected_behavior: str


class AgentDefinition(BaseModel):
    agent_id: str
    runtime_name: str
    app_name: str
    framework: str
    model: str
    description: str
    system_instruction: str
    tools: list[AgentToolDefinition]
    callbacks: list[str]
    guardrails: dict[str, Any]
    runtime: dict[str, Any]
    test_scenarios: list[AgentTestScenario]


class GuardAdminComponent(BaseModel):
    component_id: str
    name: str
    layer: str
    status: Literal[
        "operational",
        "observe_only",
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


class AgentTestRunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AgentTestEvent(BaseModel):
    type: Literal["tool_call", "tool_response", "agent_response"]
    name: str | None = None
    content: str | None = None
    arguments: dict[str, Any] | None = None
    response: Any | None = None


class AgentGuardTestDecision(BaseModel):
    trace_id: str
    tool_name: str
    decision: Decision
    risk_score: float
    explanation: str
    rules_fired: list[str]
    guard_evaluation: GuardEvaluationView | None = None


class AgentTestRunResponse(BaseModel):
    run_id: str
    session_id: str
    status: Literal["completed", "failed"]
    model: str
    user_message: str
    final_response: str
    events: list[AgentTestEvent]
    decisions: list[AgentGuardTestDecision]
    duration_ms: int
