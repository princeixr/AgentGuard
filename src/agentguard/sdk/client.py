"""AgentGuard client boundary used by framework integrations.

The in-process client preserves current behavior. A remote HTTP client will implement
the same protocol when the external interception endpoint is introduced.
"""

from __future__ import annotations

from typing import Protocol

from agentguard.firewall_v2.engine import AgentGuardFirewallV2
from agentguard.firewall_v2.models import FirewallV2Evaluation
from agentguard.intent.models import IntentContractV2
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class AgentGuardClient(Protocol):
    def evaluate(
        self,
        trace: AgentGuardTraceV1,
        intent_contract: IntentContractV2 | None = None,
    ) -> FirewallV2Evaluation:
        """Evaluate an intercepted tool proposal and return an authoritative verdict."""


class InProcessAgentGuardClient:
    """Compatibility client that delegates to the current local FirewallV2 engine."""

    def __init__(self, firewall: AgentGuardFirewallV2):
        self.firewall = firewall

    def evaluate(
        self,
        trace: AgentGuardTraceV1,
        intent_contract: IntentContractV2 | None = None,
    ) -> FirewallV2Evaluation:
        return self.firewall.evaluate(trace, intent_contract)
