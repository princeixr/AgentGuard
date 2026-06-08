"""Contracts for the Tier 3 LLM judge."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class LlmDiscoveredCriterionV1(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(default=0.0, ge=0.0, le=0.20)
    rationale: str
    escalates_risk: bool = True


class LlmJudgeInputV1(BaseModel):
    schema_version: Literal["agentguard.llm_judge_input.v1"] = (
        "agentguard.llm_judge_input.v1"
    )
    judge_input_id: str = Field(default_factory=lambda: f"judge_in_{uuid4().hex}")
    trace_id: str
    user_request: str
    tool_name: str
    arguments: dict[str, Any]
    normalized_action: dict[str, Any] | None = None
    policy_evaluation: dict[str, Any] | None = None
    prior_tier_results: list[dict[str, Any]] = Field(default_factory=list)
    trajectory_summary: str | None = None
    session_summary: dict[str, Any] = Field(default_factory=dict)


class LlmJudgeResultV1(BaseModel):
    schema_version: Literal["agentguard.llm_judge_result.v1"] = (
        "agentguard.llm_judge_result.v1"
    )
    judge_result_id: str = Field(default_factory=lambda: f"judge_{uuid4().hex}")
    trace_id: str
    verdict: Literal["allow", "require_approval", "block"]
    confidence: float = Field(ge=0.0, le=1.0)
    intent_alignment_score: float = Field(ge=0.0, le=1.0)
    tool_criticality_score: float = Field(ge=0.0, le=1.0)
    necessity_score: float = Field(ge=0.0, le=1.0)
    argument_scope_score: float = Field(ge=0.0, le=1.0)
    policy_compliance_score: float = Field(ge=0.0, le=1.0)
    context_risk_score: float = Field(ge=0.0, le=1.0)
    discovered_criteria: list[LlmDiscoveredCriterionV1] = Field(default_factory=list)
    rationale: str
    uncertainties: list[str] = Field(default_factory=list)
    model: str
    prompt_version: str
    latency_ms: int = 0
    raw_response: dict[str, Any] | None = None
