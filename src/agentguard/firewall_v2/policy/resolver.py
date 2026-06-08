"""Resolve the active policy assigned to the demo deployment."""

from __future__ import annotations

from agentguard.control_plane.registry import (
    DEMO_AGENT_ID,
    DEMO_DEPLOYMENT_ID,
    DEMO_WORKSPACE_ID,
)
from agentguard.firewall_v2.policy.loader import LoadedPolicy, PolicyLoader


def resolve_demo_policy(loader: PolicyLoader | None = None) -> LoadedPolicy:
    return (loader or PolicyLoader()).load(
        workspace_id=DEMO_WORKSPACE_ID,
        agent_id=DEMO_AGENT_ID,
        deployment_id=DEMO_DEPLOYMENT_ID,
    )
