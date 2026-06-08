"""Observe-only FirewallV2 contracts used during phased rollout."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from agentguard.core.models import utc_now

FirewallMode = Literal["v1", "v2_shadow", "v2"]


class V2StageResult(BaseModel):
    name: str
    status: Literal[
        "not_started",
        "completed",
        "failed",
        "not_implemented",
        "skipped",
    ]
    detail: str


class FirewallV2Evaluation(BaseModel):
    schema_version: Literal["agentguard.firewall_v2_evaluation.v1"] = (
        "agentguard.firewall_v2_evaluation.v1"
    )
    evaluation_id: str = Field(default_factory=lambda: f"eval_{uuid4().hex}")
    timestamp: datetime = Field(default_factory=utc_now, alias="@timestamp")
    firewall_version: str = "agentguard_firewall_v2_skeleton"
    firewall_mode: FirewallMode
    enforcement_status: Literal["observe_only", "enforced", "not_implemented"] = (
        "observe_only"
    )
    recommendation: Literal[
        "allow",
        "require_approval",
        "block",
        "not_available",
    ] = "not_available"
    stages: list[V2StageResult]
    tool_descriptor: dict[str, Any] | None = None
    normalized_action: dict[str, Any] | None = None
    policy_evaluation: dict[str, Any] | None = None
    explanation: str
