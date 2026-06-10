"""Resolve the active policy from its declared framework-neutral scope."""

from __future__ import annotations

import json

from agentguard.firewall_v2.policy.loader import LoadedPolicy, PolicyLoader


def resolve_demo_policy(loader: PolicyLoader | None = None) -> LoadedPolicy:
    policy_loader = loader or PolicyLoader()
    payload = json.loads(policy_loader.default_path.read_text(encoding="utf-8"))
    scope = payload["scope"]
    return policy_loader.load(
        workspace_id=scope["workspace_id"],
        agent_id=scope["agent_id"],
        deployment_id=scope.get("deployment_id"),
    )
