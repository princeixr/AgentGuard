"""Capability-based tool descriptors for AgentGuardFirewallV2."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolDescriptorV1(BaseModel):
    schema_version: Literal["agentguard.tool_descriptor.v1"] = (
        "agentguard.tool_descriptor.v1"
    )
    tool_name: str
    provider: str
    category: str
    domain: str = "unknown"
    operation: str = "unknown"
    capabilities: list[str] = Field(default_factory=list)
    side_effect: str | None = None
    impact: Literal["low", "medium", "high", "dynamic", "unknown"] = "unknown"
    reversible: bool | None = None
    normalizer: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    argument_roles: dict[str, list[str]] = Field(default_factory=dict)
    required_arguments: list[str] = Field(default_factory=list)
    external_impact: bool | None = None
    privilege_level: str = "standard"
    declared_data_classes: list[str] = Field(default_factory=list)
    metadata_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata_provenance: list[str] = Field(default_factory=list)
    default_tiers: list[str] = Field(default_factory=lambda: ["tier_1"])
    metadata_status: Literal["built_in", "inferred", "unsupported"] = "inferred"
    description: str | None = None
