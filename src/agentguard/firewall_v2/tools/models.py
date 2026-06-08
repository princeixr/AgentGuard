"""Capability-based tool descriptors for AgentGuardFirewallV2."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ToolDescriptorV1(BaseModel):
    schema_version: Literal["agentguard.tool_descriptor.v1"] = (
        "agentguard.tool_descriptor.v1"
    )
    tool_name: str
    provider: str
    category: str
    capabilities: list[str] = Field(default_factory=list)
    side_effect: str | None = None
    impact: Literal["low", "medium", "high", "dynamic", "unknown"] = "unknown"
    reversible: bool | None = None
    normalizer: str
    default_tiers: list[str] = Field(default_factory=lambda: ["tier_1"])
    metadata_status: Literal["built_in", "inferred", "unsupported"] = "inferred"
    description: str | None = None

