"""Canonical AgentGuard v1 trace and governance schemas.

These models are the stable contract for historical OpenClaw traces, live Google ADK
interceptions, Elastic indexing, statistical scoring, decisions, and session risk state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agentguard.core.models import utc_now


class AgentGuardSchemaV1Model(BaseModel):
    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)


class TraceSourceV1(AgentGuardSchemaV1Model):
    mode: Literal["historical", "live"]
    agent_framework: Literal["openclaw", "google_adk", "mock", "synthetic"]
    source_type: str
    agent_id: str
    workspace_id: str | None = None
    deployment_id: str | None = None
    integration_id: str | None = None
    runtime_agent_id: str | None = None
    agent_config_id: str | None = None
    scenario_id: str | None = None
    run_id: str | None = None
    environment_id: str | None = None


class ExplicitConstraintV1(AgentGuardSchemaV1Model):
    constraint_type: str
    text: str
    forbidden_tool: str | None = None
    forbidden_data_scope: str | None = None


class IntentContractV1(AgentGuardSchemaV1Model):
    raw_user_request: str
    normalized_intent: str
    task_goal: str | None = None
    domain: str
    task_category: str
    available_tools: list[str] = Field(default_factory=list)
    task_relevant_tools: list[str] = Field(default_factory=list)
    intent_forbidden_tools: list[str] = Field(default_factory=list)
    confirmation_required_tools: list[str] = Field(default_factory=list)
    explicit_constraints: list[ExplicitConstraintV1] = Field(default_factory=list)
    allowed_data_scopes: list[str] = Field(default_factory=list)
    forbidden_data_scopes: list[str] = Field(default_factory=list)


class ToolCallV1(AgentGuardSchemaV1Model):
    call_id: str
    tool_name: str
    tool_category: str
    mcp_server: str | None = None
    risk_level: str
    side_effect_type: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    argument_summary: str
    argument_hash: str | None = None


class TrajectoryV1(AgentGuardSchemaV1Model):
    prior_tool_names: list[str] = Field(default_factory=list)
    prior_tool_sequence: str = ""
    prior_tool_count: int = 0
    previous_tool_name: str | None = None
    previous_output_summary: str | None = None
    prior_side_effect_count: int = 0
    prior_blocked_count: int = 0
    prior_approval_required_count: int = 0


class ToolOutputContextV1(AgentGuardSchemaV1Model):
    contains_untrusted_instruction: bool = False
    contains_external_link: bool = False
    contains_secret_like_content: bool = False
    output_influenced_current_call: bool = False


class RetrievalTextV1(AgentGuardSchemaV1Model):
    summary: str
    intent_text: str
    trajectory_text: str
    argument_text: str


class ExecutionStateV1(AgentGuardSchemaV1Model):
    status: Literal["proposed", "executed", "blocked_by_guard", "failed"]
    executed_at: datetime | None = None
    latency_ms: int | None = None
    output_summary: str | None = None
    output_ref: str | None = None


class AgentGuardTraceV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.trace.v1"] = "agentguard.trace.v1"
    trace_id: str
    session_id: str
    previous_trace_id: str | None = None
    step_index: int
    timestamp: datetime = Field(default_factory=utc_now, alias="@timestamp")
    source: TraceSourceV1
    intent: IntentContractV1
    proposed_tool_call: ToolCallV1
    trajectory: TrajectoryV1
    tool_output_context: ToolOutputContextV1 = Field(default_factory=ToolOutputContextV1)
    retrieval_text: RetrievalTextV1
    execution: ExecutionStateV1


class LiveEventV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.live_event.v1"] = "agentguard.live_event.v1"
    event_id: str
    timestamp: datetime = Field(default_factory=utc_now, alias="@timestamp")
    event_type: Literal[
        "tool_proposed",
        "guard_scored",
        "guard_decided",
        "tool_executed",
        "tool_blocked",
        "tool_failed",
    ]
    trace_id: str | None = None
    session_id: str
    step_index: int | None = None
    agent_framework: str
    agent_id: str
    workspace_id: str | None = None
    deployment_id: str | None = None
    integration_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RetrievalFeatureV1(AgentGuardSchemaV1Model):
    query_text: str
    top_k: int = 0
    approved_trace_ids: list[str] = Field(default_factory=list)
    blocked_trace_ids: list[str] = Field(default_factory=list)
    max_approved_similarity: float = 0.0
    max_blocked_similarity: float = 0.0
    mean_approved_similarity: float = 0.0
    mean_blocked_similarity: float = 0.0
    blocked_neighbor_ratio: float = 0.0


class HistoricalStatisticsV1(AgentGuardSchemaV1Model):
    tool_prior_count: int = 0
    tool_given_intent_count: int = 0
    tool_given_intent_probability: float = 0.0
    tool_given_previous_tool_probability: float = 0.0
    sequence_percentile_rarity: float = 0.0
    argument_cluster_distance: float = 0.0
    historical_block_rate_for_tool_intent: float = 0.0
    historical_approval_rate_for_tool_intent: float = 0.0


class PolicyFeaturesV1(AgentGuardSchemaV1Model):
    tool_in_task_relevant_set: bool = False
    tool_in_intent_forbidden_set: bool = False
    requires_confirmation: bool = False
    explicit_constraint_violated: bool = False
    domain_allowed: bool = True
    data_scope_violation: bool = False
    side_effect_present: bool = False
    irreversible_side_effect: bool = False


class ContextFeaturesV1(AgentGuardSchemaV1Model):
    untrusted_instruction_present: bool = False
    external_link_present: bool = False
    secret_like_content_present: bool = False
    previous_output_to_tool_similarity: float = 0.0
    intent_to_tool_similarity: float = 0.0


class TraceFeatureV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.trace_features.v1"] = "agentguard.trace_features.v1"
    feature_id: str
    trace_id: str
    session_id: str
    workspace_id: str | None = None
    agent_id: str | None = None
    deployment_id: str | None = None
    step_index: int
    timestamp: datetime = Field(default_factory=utc_now, alias="@timestamp")
    retrieval: RetrievalFeatureV1
    historical_statistics: HistoricalStatisticsV1 = Field(default_factory=HistoricalStatisticsV1)
    policy_features: PolicyFeaturesV1 = Field(default_factory=PolicyFeaturesV1)
    context_features: ContextFeaturesV1 = Field(default_factory=ContextFeaturesV1)


class ComponentScoresV1(AgentGuardSchemaV1Model):
    intent_drift: float = Field(ge=0.0, le=1.0)
    sequence_deviation: float = Field(ge=0.0, le=1.0)
    argument_drift: float = Field(ge=0.0, le=1.0)
    permission_risk: float = Field(ge=0.0, le=1.0)
    tool_output_susceptibility: float = Field(ge=0.0, le=1.0)
    retrieval_risk: float = Field(ge=0.0, le=1.0)
    step_risk: float = Field(ge=0.0, le=1.0)


class CumulativeScoresV1(AgentGuardSchemaV1Model):
    cumulative_intent_drift: float = Field(default=0.0, ge=0.0, le=1.0)
    cumulative_sequence_deviation: float = Field(default=0.0, ge=0.0, le=1.0)
    cumulative_argument_drift: float = Field(default=0.0, ge=0.0, le=1.0)
    cumulative_permission_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    cumulative_session_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    drift_streak: int = 0
    high_risk_streak: int = 0


class GuardScoreV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.guard_score.v1"] = "agentguard.guard_score.v1"
    score_id: str
    trace_id: str
    feature_id: str
    session_id: str
    workspace_id: str | None = None
    agent_id: str | None = None
    deployment_id: str | None = None
    step_index: int
    guard_version: str
    timestamp: datetime = Field(default_factory=utc_now, alias="@timestamp")
    component_scores: ComponentScoresV1
    cumulative_before: CumulativeScoresV1 = Field(default_factory=CumulativeScoresV1)
    cumulative_after: CumulativeScoresV1
    dominant_signals: list[str] = Field(default_factory=list)


class DecisionThresholdsV1(AgentGuardSchemaV1Model):
    warn: float = 0.35
    review: float = 0.55
    require_approval: float = 0.70
    block: float = 0.85


class DecisionRetrievalEvidenceV1(AgentGuardSchemaV1Model):
    approved_trace_ids: list[str] = Field(default_factory=list)
    blocked_trace_ids: list[str] = Field(default_factory=list)
    top_blocked_similarity: float = 0.0
    top_approved_similarity: float = 0.0


class LlmJudgeV1(AgentGuardSchemaV1Model):
    used: bool = False
    model: str | None = None
    verdict: str | None = None
    confidence: float | None = None
    rationale: str | None = None


class GuardDecisionV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.guard_decision.v1"] = "agentguard.guard_decision.v1"
    decision_id: str
    trace_id: str
    score_id: str | None = None
    session_id: str
    workspace_id: str | None = None
    agent_id: str | None = None
    deployment_id: str | None = None
    step_index: int
    timestamp: datetime = Field(default_factory=utc_now, alias="@timestamp")
    decision: Literal["allow", "warn", "review", "require_approval", "block"]
    tier_used: Literal[
        "static_policy",
        "retrieval_scoring",
        "cumulative_risk",
        "llm_judge",
        "decision_policy",
    ]
    final_risk_score: float = Field(ge=0.0, le=1.0)
    thresholds: DecisionThresholdsV1 = Field(default_factory=DecisionThresholdsV1)
    decision_rules_fired: list[str] = Field(default_factory=list)
    retrieval_evidence: DecisionRetrievalEvidenceV1 = Field(default_factory=DecisionRetrievalEvidenceV1)
    llm_judge: LlmJudgeV1 = Field(default_factory=LlmJudgeV1)
    explanation: str
    latency_ms: int


class RecentRiskWindowEntryV1(AgentGuardSchemaV1Model):
    trace_id: str
    tool_name: str
    intent_drift: float = Field(ge=0.0, le=1.0)
    step_risk: float = Field(ge=0.0, le=1.0)


class SessionRiskCountersV1(AgentGuardSchemaV1Model):
    approval_required_count: int = 0
    blocked_count: int = 0


class SessionRiskStateV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.session_risk.v1"] = "agentguard.session_risk.v1"
    session_id: str
    workspace_id: str | None = None
    deployment_id: str | None = None
    agent_framework: str
    agent_id: str
    last_trace_id: str | None = None
    last_score_id: str | None = None
    last_step_index: int = 0
    updated_at: datetime = Field(default_factory=utc_now)
    tool_sequence: list[str] = Field(default_factory=list)
    risk_state: CumulativeScoresV1 = Field(default_factory=CumulativeScoresV1)
    max_single_step_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    counters: SessionRiskCountersV1 = Field(default_factory=SessionRiskCountersV1)
    recent_window: list[RecentRiskWindowEntryV1] = Field(default_factory=list)


class LabelRubricScoresV1(AgentGuardSchemaV1Model):
    intent_relevance: int = Field(ge=0, le=4)
    sequence_coherence: int = Field(ge=0, le=4)
    argument_appropriateness: int = Field(ge=0, le=4)
    permission_sensitivity: int = Field(ge=0, le=4)
    data_minimization: int = Field(ge=0, le=4)
    tool_output_susceptibility: int = Field(ge=0, le=4)
    overall_appropriateness: int = Field(ge=0, le=4)


class LabelRecordV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.label.v1"] = "agentguard.label.v1"
    label_id: str
    trace_id: str
    labeler_id: str
    timestamp: datetime = Field(default_factory=utc_now, alias="@timestamp")
    rubric_scores: LabelRubricScoresV1
    gold_verdict: Literal["allow", "warn", "review", "require_approval", "block"]
    failure_type: str
    label_confidence: Literal["low", "medium", "high"]
    rationale_summary: str


class ScenarioRecordV1(AgentGuardSchemaV1Model):
    schema_version: Literal["agentguard.scenario.v1"] = "agentguard.scenario.v1"
    scenario_id: str
    domain: str
    task_category: str
    user_request: str
    expected_allowed_tools: list[str] = Field(default_factory=list)
    expected_disallowed_tools: list[str] = Field(default_factory=list)
    expected_constraints: list[str] = Field(default_factory=list)
    failure_type: str = "none"
    agent_behavior_mode: str = "clean"
    gold_final_verdict: str = "allow"
