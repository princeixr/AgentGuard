"""Control-plane identity models for the AgentGuard demo."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from agentguard.core.models import utc_now


class RuntimeIdentity(BaseModel):
    workspace_id: str
    agent_id: str
    deployment_id: str
    integration_id: str


class UserRecord(BaseModel):
    user_id: str
    workspace_id: str
    name: str
    email: str
    role: Literal["owner", "admin", "operator", "viewer"] = "owner"


class WorkspaceRecord(BaseModel):
    workspace_id: str
    name: str
    plan: str = "Demo"
    created_at: datetime = Field(default_factory=utc_now)


class DeploymentRecord(BaseModel):
    deployment_id: str
    workspace_id: str
    agent_id: str
    environment: str
    runtime_framework: str
    runtime_agent_name: str
    version: str = "development"
    status: Literal["live", "stale", "offline"] = "live"
    last_seen_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRecord(BaseModel):
    agent_id: str
    workspace_id: str
    name: str
    description: str
    framework: str
    status: Literal["live", "stale", "offline", "setup_required"] = "live"
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str
    default_policy_id: str
    last_seen_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
    deployments: list[DeploymentRecord] = Field(default_factory=list)
