"""Factory helpers for required governance baselines."""

from agentguard.governance.guard_engine import GuardEngine


def build_guard(name: str) -> GuardEngine:
    if name not in {"rule_only", "stateless_intent", "full_agentguard"}:
        raise ValueError(f"Unknown guard baseline: {name}")
    return GuardEngine(mode=name)

