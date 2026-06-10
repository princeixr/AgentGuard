"""Policy validation beyond the Pydantic document schema."""

from __future__ import annotations

from agentguard.firewall_v2.policy.models import PolicyDocumentV1


class PolicyValidationError(ValueError):
    """Raised when a policy cannot be safely activated."""


def validate_policy_scope(
    policy: PolicyDocumentV1,
    *,
    workspace_id: str,
    agent_id: str,
    deployment_id: str | None = None,
) -> None:
    if policy.scope.workspace_id != workspace_id:
        raise PolicyValidationError(
            f"Policy workspace {policy.scope.workspace_id!r} does not match "
            f"{workspace_id!r}."
        )
    if policy.scope.agent_id != agent_id:
        raise PolicyValidationError(
            f"Policy agent {policy.scope.agent_id!r} does not match {agent_id!r}."
        )
    if (
        deployment_id is not None
        and policy.scope.deployment_id is not None
        and policy.scope.deployment_id != deployment_id
    ):
        raise PolicyValidationError(
            f"Policy deployment {policy.scope.deployment_id!r} does not match "
            f"{deployment_id!r}."
        )
