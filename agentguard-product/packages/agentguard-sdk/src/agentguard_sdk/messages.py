"""Agent-facing enforcement messages."""

from __future__ import annotations

from typing import Any


def agent_facing_enforcement_message(
    decision: str,
    matched_rules: list[dict[str, Any]] | None = None,
) -> str:
    capability = _matched_capability(matched_rules or [], decision)
    if decision == "block":
        reason = (
            f"{capability} is prohibited by policy"
            if capability
            else "the requested action is prohibited by policy"
        )
        return f"AgentGuard blocked this tool call because {reason}."

    reason = (
        f"{capability} modifies external state"
        if capability
        else "the requested action may modify external state"
    )
    return (
        f"AgentGuard paused this tool call because {reason}. "
        "Administrator approval is required to proceed."
    )


def administrator_rejection_message() -> str:
    return (
        "AgentGuard blocked this tool call because the approval request was "
        "rejected by your administrator."
    )


def _matched_capability(
    matched_rules: list[dict[str, Any]],
    decision: str,
) -> str | None:
    for rule in matched_rules:
        if rule.get("effect") != decision:
            continue
        capabilities = rule.get("matched_capabilities")
        if isinstance(capabilities, list):
            for capability in capabilities:
                if isinstance(capability, str) and capability:
                    return capability
    return None
