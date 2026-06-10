"""Contracts for turn-scoped user authorization."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from agentguard.core.models import utc_now
from agentguard.firewall_v2.tiers.models import TierRecommendation


class IntentConstraintV1(BaseModel):
    type: Literal[
        "negative_action",
        "resource_scope",
        "destination_scope",
        "amount_limit",
        "confirmation",
        "other",
    ]
    text: str
    capability: str | None = None
    value: str | None = None


class IntentExtractionPayloadV1(BaseModel):
    requested_capabilities: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    permitted_resources: list[str] = Field(default_factory=list)
    forbidden_resources: list[str] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    side_effect_authorized: bool = False
    confirmation_language_present: bool = False
    constraints: list[IntentConstraintV1] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainties: list[str] = Field(default_factory=list)


class IntentExtractorEvidenceV1(BaseModel):
    name: str
    version: str
    model: str | None = None
    method: Literal["llm_structured", "deterministic_fallback"]
    status: Literal["completed", "fallback"]
    confidence: float = Field(ge=0.0, le=1.0)
    detail: str


class IntentContractV2(BaseModel):
    schema_version: Literal["agentguard.intent_contract.v2"] = (
        "agentguard.intent_contract.v2"
    )
    intent_id: str = Field(default_factory=lambda: f"intent_{uuid4().hex}")
    turn_id: str
    session_id: str
    agent_id: str
    created_at: datetime = Field(default_factory=utc_now)
    raw_user_request: str
    requested_capabilities: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    permitted_resources: list[str] = Field(default_factory=list)
    forbidden_resources: list[str] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    side_effect_authorized: bool = False
    confirmation_language_present: bool = False
    constraints: list[IntentConstraintV1] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    extractor: IntentExtractorEvidenceV1


class IntentAuthorizationV1(BaseModel):
    schema_version: Literal["agentguard.intent_authorization.v1"] = (
        "agentguard.intent_authorization.v1"
    )
    intent_id: str
    recommendation: TierRecommendation
    matched_requested_capabilities: list[str] = Field(default_factory=list)
    matched_forbidden_capabilities: list[str] = Field(default_factory=list)
    unauthorized_capabilities: list[str] = Field(default_factory=list)
    matched_resources: list[str] = Field(default_factory=list)
    forbidden_resources: list[str] = Field(default_factory=list)
    destination_violations: list[str] = Field(default_factory=list)
    explanation: str
