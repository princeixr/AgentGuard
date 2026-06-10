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
from agentguard.firewall_v2.config import FirewallV2RuntimeConfig
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy


def guard_admin_status(agent_id: str) -> GuardAdminStatus:
    definition = agent_definition()
    guardrails = definition["guardrails"]
    loaded_policy = resolve_demo_policy()
    policy = loaded_policy.document
    mode = guardrails["firewall_mode"]
    runtime_config = FirewallV2RuntimeConfig.from_env()
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
            component_id="tool_descriptors",
            name="Tool capability registry",
            layer="V2 foundation",
            status="operational",
            summary=(
                "Runtime and MCP metadata resolve into security descriptors with "
                "capabilities, operations, argument roles, provenance, and confidence."
            ),
            management=(
                "Structured tools are inferred automatically. Low-confidence metadata "
                "falls back conservatively; declarative overrides are the next extension."
            ),
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
                "Structured tools use one metadata-driven normalizer. Shell uses a "
                "specialized parser because its behavior is encoded in command syntax."
            ),
            management=(
                "Schema argument roles populate resources, destinations, data classes, "
                "and estimated values. Unsupported syntax or weak metadata fails safely."
            ),
        ),
        GuardAdminComponent(
            component_id="agenttrust_shell",
            name="AgentTrust shell security",
            layer="Tier 1 provider",
            status=(
                "operational"
                if runtime_config.agenttrust_shell_enabled
                else "observe_only"
            ),
            summary=(
                "The real AgentTrust v0.5.0 deterministic interceptor evaluates every "
                "shell proposal using stateless command-risk and policy checks."
                if runtime_config.agenttrust_shell_enabled
                else "AgentTrust shell analysis is implemented but disabled for this process."
            ),
            management=(
                "ALLOW maps to allow; BLOCK remains a strict block; WARN, REVIEW, "
                "unknown results, and provider failures require approval. The pinned "
                "254-case shell benchmark records 92.1% AgentTrust verdict agreement "
                "and zero dangerous false allows after AgentGuard policy combination."
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
                "Central policy and deterministic security-provider results are combined "
                "using most-restrictive precedence."
            ),
            management=(
                "A policy or AgentTrust block cannot be downgraded. Approval requirements "
                "cannot be downgraded to allow."
            ),
        ),
        GuardAdminComponent(
            component_id="tier_2",
            name="Tier 2 semantic analysis",
            layer="Evaluation",
            status="placeholder",
            summary="Elastic-backed semantic retrieval and comparison are planned but not active in V2.",
            management="Will be enabled only after a verified Tier 1 baseline.",
        ),
        GuardAdminComponent(
            component_id="tier_3",
            name="Tier 3 LLM judge",
            layer="Evaluation",
            status=(
                "operational"
                if runtime_config.tier_3_enabled
                else "observe_only"
            ),
            summary=(
                "The Gemini structured-output judge participates in escalated V2 "
                "evaluations."
                if runtime_config.tier_3_enabled
                else "The Gemini structured-output judge is implemented but disabled."
            ),
            management=(
                "Controlled by AGENTGUARD_TIER_3_ENABLED and "
                "AGENTGUARD_TIER3_ENFORCEMENT_ENABLED. Deterministic policy remains "
                "non-overridable."
            ),
        ),
        GuardAdminComponent(
            component_id="decision_combiner",
            name="Deterministic decision combiner",
            layer="Enforcement",
            status="operational",
            summary=(
                "Tier results are reduced to allow, require approval, or block with "
                "deterministic precedence and recorded decision ownership."
            ),
            management=(
                "In v2 mode the combined decision controls execution. Model-based tiers "
                "cannot override deterministic policy or shell-security blocks."
            ),
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
                else "FirewallV2 is disabled for this process."
            ),
            management=(
                "Set AGENTGUARD_FIREWALL_MODE=v2 and restart API and ADK processes."
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
        "Metadata-driven normalization and AgentTrust shell security are active. Intent "
        "contracts, Tier 2 semantic analysis, approval resume, and declarative descriptor "
        "overrides remain incomplete."
    )
    return GuardAdminStatus(
        agent_id=agent_id,
        firewall_mode=mode,
        active_enforcement=(
            "firewall_v2"
            if mode == "v2"
            else "firewall_v1"
            if mode == "v2_shadow"
            else "firewall_v1"
        ),
        architecture_version="AgentGuard FirewallV2",
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
                else "This published policy is schema-validated and evaluated by FirewallV2."
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
