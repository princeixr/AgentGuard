"""Canonical normalized-action contracts used by FirewallV2."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class NormalizedResourceV1(BaseModel):
    type: Literal["filesystem_path", "network_destination", "unknown"]
    value: str
    access: str
    sensitivity: Literal["normal", "sensitive", "unknown"] = "normal"


class NormalizedDestinationV1(BaseModel):
    type: Literal["url", "host", "email", "domain", "unknown"]
    value: str
    external: bool | None = None


class ParserResultV1(BaseModel):
    name: str
    version: str
    status: Literal["parsed", "partial", "unsupported", "invalid"]
    confidence: float = Field(ge=0.0, le=1.0)
    unsupported_syntax: bool = False
    detail: str


class NormalizedActionV1(BaseModel):
    schema_version: Literal["agentguard.normalized_action.v1"] = (
        "agentguard.normalized_action.v1"
    )
    action_id: str = Field(default_factory=lambda: f"act_{uuid4().hex}")
    trace_id: str
    tool_name: str
    capabilities: list[str] = Field(default_factory=list)
    operation: str
    resources: list[NormalizedResourceV1] = Field(default_factory=list)
    destinations: list[NormalizedDestinationV1] = Field(default_factory=list)
    side_effect: bool
    reversible: bool | None
    impact: Literal["low", "medium", "high", "unknown"]
    flags: list[str] = Field(default_factory=list)
    parser: ParserResultV1
    argument_hash: str | None = None
