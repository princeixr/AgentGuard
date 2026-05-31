"""Factory helpers for required governance baselines."""

from agentguard.governance.firewall_v1 import AgentGuardFirewallV1


def build_guard(name: str) -> AgentGuardFirewallV1:
    if name not in {"rule_only", "stateless_intent", "full_agentguard"}:
        raise ValueError(f"Unknown guard baseline: {name}")
    # The v1 firewall currently uses one deterministic scoring path. Baseline-specific
    # scoring strategies will be plugged into this factory when evaluation work resumes.
    return AgentGuardFirewallV1(namespace=f"replay_{name}")
