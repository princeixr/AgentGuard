"""Shared contracts for FirewallV2 tier outputs."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

TierRecommendation = Literal["allow", "require_approval", "block", "not_available"]


class TierSignalV1(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    rationale: str


class TierResultV1(BaseModel):
    schema_version: Literal["agentguard.tier_result.v1"] = "agentguard.tier_result.v1"
    tier_result_id: str = Field(default_factory=lambda: f"tier_{uuid4().hex}")
    tier: Literal["tier_1", "tier_2", "tier_3"]
    status: Literal["completed", "skipped", "failed", "not_available"]
    recommendation: TierRecommendation = "not_available"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[TierSignalV1] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    escalation_reason: str | None = None
    explanation: str
    latency_ms: int = 0
