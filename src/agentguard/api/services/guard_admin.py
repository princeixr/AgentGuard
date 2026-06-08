"""Truthful Guard Admin status for the phased FirewallV2 rollout."""

from __future__ import annotations

import os

from agentguard.api.models import (
    AgentToolDefinition,
    GuardAdminComponent,
    GuardAdminPolicy,
    GuardAdminStatus,
)
from agentguard.control_plane.demo_adk_definition import agent_definition
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy


def guard_admin_status(agent_id: str) -> GuardAdminStatus:
    definition = agent_definition()
    guardrails = definition["guardrails"]
    loaded_policy = resolve_demo_policy()
    policy = loaded_policy.document
    mode = guardrails["firewall_mode"]
    force_block = _env_bool("AGENTGUARD_FORCE_BLOCK", fallback="FORCE_BLOCK")
    components = [
        GuardAdminComponent(
            component_id="interception",
            name="Google ADK interception",
            layer="Runtime",
            status="operational",
            summary="ADK before/after tool callbacks create canonical traces and execution events.",
            management="Configured in the integrated agent callback registration.",
        ),
        GuardAdminComponent(
            component_id="firewall_v1",
            name="FirewallV1 enforcement",
            layer="Legacy enforcement",
            status="operational",
            summary=(
                "The heuristic V1 path is retained as comparison evidence."
                if mode == "v2"
                else "The heuristic V1 path remains the active enforcement owner."
            ),
            management=(
                "Not used for the effective runtime decision in v2 mode."
                if mode == "v2"
                else "Temporary compatibility layer while V2 is developed and verified."
            ),
        ),
        GuardAdminComponent(
            component_id="tool_descriptors",
            name="Tool capability registry",
            layer="V2 foundation",
            status="operational",
            summary="Known tools resolve to capabilities, impact, reversibility, and a normalizer ID.",
            management="Built-in descriptors are code-defined; custom registration is not implemented.",
        ),
        GuardAdminComponent(
            component_id="policy_engine",
            name="Versioned policy engine",
            layer="Central guardrail",
            status="operational",
            summary=(
                "A validated published policy is loaded and evaluated against tool "
                "capabilities for each V2 interception."
            ),
            management=(
                "Guard Admin validates and atomically publishes edits as a new patch "
                "version. V2 reloads the active policy for every interception."
            ),
        ),
        GuardAdminComponent(
            component_id="normalization",
            name="Action normalizers",
            layer="V2 normalization",
            status="operational",
            summary=(
                "The shell normalizer emits canonical actions for supported single "
                "commands. Gmail and future MCP normalizers are not implemented yet."
            ),
            management=(
                "Unsupported shell syntax is intentionally low-confidence and falls "
                "back to policy parser-failure handling."
            ),
        ),
        GuardAdminComponent(
            component_id="intent_contract",
            name="Intent contract",
            layer="V2 authorization",
            status="not_implemented",
            summary="User authorization is not yet extracted into a reusable V2 intent contract.",
            management="Phase 5 will add deterministic extraction and conservative fallback.",
        ),
        GuardAdminComponent(
            component_id="tier_1",
            name="Tier 1 deterministic checks",
            layer="Evaluation",
            status="operational",
            summary=(
                "Tool descriptors, normalized shell actions, policy defaults, matched "
                "rules, and restrictive precedence produce the V2 decision."
            ),
            management=(
                "Enforced in v2 mode and recorded without enforcement in v2_shadow."
            ),
        ),
        GuardAdminComponent(
            component_id="tier_2",
            name="Tier 2 semantic analysis",
            layer="Evaluation",
            status="not_implemented",
            summary="Elastic-backed semantic retrieval and comparison are planned but not active in V2.",
            management="Will be enabled only after a verified Tier 1 baseline.",
        ),
        GuardAdminComponent(
            component_id="tier_3",
            name="Tier 3 LLM judge",
            layer="Evaluation",
            status="not_implemented",
            summary="No LLM judge currently participates in FirewallV2 decisions.",
            management="Will be optional and constrained by deterministic policy precedence.",
        ),
        GuardAdminComponent(
            component_id="approval_resume",
            name="Approval and resume",
            layer="Enforcement",
            status="not_implemented",
            summary="Approval-required calls are stopped, but dashboard approval cannot resume ADK execution.",
            management="A resumable execution contract is required before enabling this control.",
        ),
        GuardAdminComponent(
            component_id="v2_shadow",
            name="V2 runtime mode",
            layer="Observability",
            status=(
                "operational"
                if mode == "v2"
                else "observe_only"
                if mode == "v2_shadow"
                else "placeholder"
            ),
            summary=(
                "V2 deterministic policy decisions control tool execution."
                if mode == "v2"
                else "V2 stage and descriptor evidence is recorded beside V1 decisions."
                if mode == "v2_shadow"
                else "Enable v2_shadow to record V2 rollout evidence beside V1 decisions."
            ),
            management=(
                "Set AGENTGUARD_FIREWALL_MODE to v1, v2_shadow, or v2 and restart "
                "API and ADK processes."
            ),
        ),
    ]
    warnings = []
    if force_block:
        warnings.append(
            "AGENTGUARD_FORCE_BLOCK is enabled. Every tool call is blocked before normal "
            "V1 risk and threshold logic can determine the outcome."
        )
    warnings.append(
        "Shell paths are normalized, but Gmail recipients, payment amounts, calendar "
        "targets, intent contracts, Tier 2, and Tier 3 are not implemented."
    )
    return GuardAdminStatus(
        agent_id=agent_id,
        firewall_mode=mode,
        active_enforcement=(
            "firewall_v2_deterministic" if mode == "v2" else "firewall_v1"
        ),
        architecture_version="FirewallV2 deterministic policy enforcement",
        force_block_enabled=force_block,
        approval_enforced=guardrails["approval_enforced"],
        policy=GuardAdminPolicy(
            policy_id=policy.policy_id,
            version=policy.version,
            status="operational",
            source=str(loaded_policy.path),
            editable=True,
            explanation=(
                "This published policy is schema-validated, editable, and controls "
                "deterministic V2 execution decisions."
                if mode == "v2"
                else (
                    "This published policy is schema-validated, editable, and used for "
                    "V2 shadow recommendations. FirewallV1 owns execution enforcement."
                )
            ),
            effective_hash=loaded_policy.effective_hash,
            rule_count=len(policy.rules),
            defaults=policy.defaults.model_dump(mode="json"),
        ),
        components=components,
        tools=[
            AgentToolDefinition.model_validate(tool)
            for tool in definition["tools"]
        ],
        warnings=warnings,
    )


def _env_bool(name: str, fallback: str | None = None) -> bool:
    value = os.environ.get(name)
    if value is None and fallback is not None:
        value = os.environ.get(fallback)
    return (value or "false").strip().lower() in {"1", "true", "yes", "on"}
