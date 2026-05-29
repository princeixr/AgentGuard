"""Pydantic models that form the shared AgentGuard data contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agentguard.core.enums import FailureType, ToolRiskLevel, Verdict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentGuardModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True)


class UserIntent(AgentGuardModel):
    session_id: str
    raw_request: str
    normalized_intent: str
    allowed_domains: list[str]
    allowed_tools: list[str]
    disallowed_tools: list[str] = Field(default_factory=list)
    requires_confirmation_for: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ProposedToolCall(AgentGuardModel):
    call_id: str
    session_id: str
    step_index: int
    tool_name: str
    tool_category: str
    risk_level: ToolRiskLevel
    arguments: dict[str, Any] = Field(default_factory=dict)
    argument_summary: str
    argument_hash: str | None = None
    proposed_by: str
    timestamp: datetime = Field(default_factory=utc_now)


class ExecutedToolCall(AgentGuardModel):
    call_id: str
    session_id: str
    step_index: int
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output_summary: str
    output_raw_ref: str | None = None
    status: Literal["executed", "blocked", "failed", "skipped"]
    latency_ms: int | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class ToolOutputContext(AgentGuardModel):
    immediate_prior_output_summary: str | None = None
    contains_untrusted_instruction: bool = False
    contains_external_link: bool = False
    contains_secret_like_content: bool = False
    output_influenced_current_call: bool = False


class RawTraceRecord(AgentGuardModel):
    trace_id: str
    session_id: str
    agent_id: str
    agent_framework: str
    domain: str
    task_category: str
    user_intent: UserIntent
    system_prompt_hash: str | None = None
    tool_schema_snapshot_id: str | None = None
    step_index: int
    proposed_tool_call: ProposedToolCall
    prior_tool_calls: list[ExecutedToolCall] = Field(default_factory=list)
    tool_output_context: ToolOutputContext = Field(default_factory=ToolOutputContext)
    execution_status: Literal["proposed", "executed", "blocked_by_guard", "failed"]
    source_type: Literal[
        "live",
        "live_openclaw",
        "live_google_adk",
        "synthetic",
        "synthetic_clean",
        "synthetic_adversarial",
        "adapted_benchmark",
    ]
    created_at: datetime = Field(default_factory=utc_now)


class LabelRecord(AgentGuardModel):
    trace_id: str
    labeler_id: str
    intent_relevance: int = Field(ge=0, le=4)
    sequence_coherence: int = Field(ge=0, le=4)
    argument_appropriateness: int = Field(ge=0, le=4)
    permission_sensitivity: int = Field(ge=0, le=4)
    data_minimization: int = Field(ge=0, le=4)
    tool_output_susceptibility: int = Field(ge=0, le=4)
    overall_appropriateness: int = Field(ge=0, le=4)
    gold_verdict: Verdict
    failure_type: FailureType
    label_confidence: Literal["low", "medium", "high"]
    rationale_summary: str


class GuardDecision(AgentGuardModel):
    trace_id: str
    guard_version: str
    decision: Verdict
    tier_used: Literal[
        "static_policy",
        "trace_retrieval",
        "intent_alignment",
        "llm_fallback",
        "decision_policy",
    ]
    risk_score: float = Field(ge=0.0, le=1.0)
    similarity_to_approved_trace: float | None = None
    similarity_to_blocked_trace: float | None = None
    trajectory_drift_score: float | None = None
    argument_novelty_score: float | None = None
    cumulative_session_risk: float | None = None
    latency_ms: int
    explanation: str
    created_at: datetime = Field(default_factory=utc_now)


class ScenarioRecord(AgentGuardModel):
    scenario_id: str
    domain: str
    task_category: str
    user_request: str
    expected_allowed_tools: list[str] = Field(default_factory=list)
    expected_disallowed_tools: list[str] = Field(default_factory=list)
    failure_type: FailureType = FailureType.NONE
    agent_behavior_mode: str = "clean"
    gold_final_verdict: Verdict = Verdict.ALLOW


class MetricReport(AgentGuardModel):
    accuracy: float | None = None
    harmful_call_recall: float | None = None
    false_positive_rate: float | None = None
    macro_f1: float | None = None
    clean_session_false_intervention_rate: float | None = None
    attack_success_reduction: float | None = None
    p50_latency_ms: int | None = None
    p95_latency_ms: int | None = None


class DemoReport(AgentGuardModel):
    title: str
    summary: str
    metrics: MetricReport | None = None
    generated_at: datetime = Field(default_factory=utc_now)
