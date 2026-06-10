"""Environment-backed runtime flags for FirewallV2 tiers."""

from __future__ import annotations

import os

from pydantic import BaseModel


class FirewallV2RuntimeConfig(BaseModel):
    tier_1_enabled: bool = True
    agenttrust_shell_enabled: bool = True
    intent_llm_enabled: bool = True
    intent_confidence_threshold: float = 0.70
    tier_2_enabled: bool = False
    tier_3_enabled: bool = False
    tier_3_enforcement_enabled: bool = False
    mock_pipeline_only: bool = False
    tier_confidence_threshold: float = 0.75

    @classmethod
    def from_env(cls) -> "FirewallV2RuntimeConfig":
        tier_3_enabled = _env_bool(
            "AGENTGUARD_TIER_3_ENABLED",
            fallback="AGENTGUARD_TIER3_SHADOW_ENABLED",
            default=False,
        )
        return cls(
            tier_1_enabled=_env_bool("AGENTGUARD_TIER_1_ENABLED", default=True),
            agenttrust_shell_enabled=_env_bool(
                "AGENTGUARD_AGENTTRUST_SHELL_ENABLED",
                default=True,
            ),
            intent_llm_enabled=_env_bool(
                "AGENTGUARD_INTENT_LLM_ENABLED",
                default=True,
            ),
            intent_confidence_threshold=float(
                os.environ.get("AGENTGUARD_INTENT_CONFIDENCE_THRESHOLD", "0.70")
            ),
            tier_2_enabled=_env_bool("AGENTGUARD_TIER_2_ENABLED", default=False),
            tier_3_enabled=tier_3_enabled,
            tier_3_enforcement_enabled=_env_bool(
                "AGENTGUARD_TIER3_ENFORCEMENT_ENABLED",
                default=False,
            ),
            mock_pipeline_only=_env_bool(
                "AGENTGUARD_MOCK_PIPELINE_ONLY",
                fallback="AGENTGUARD_MOCK_RUN",
                default=False,
            ),
            tier_confidence_threshold=float(
                os.environ.get("AGENTGUARD_TIER_CONFIDENCE_THRESHOLD", "0.75")
            ),
        )


def _env_bool(name: str, fallback: str | None = None, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None and fallback is not None:
        value = os.environ.get(fallback)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
