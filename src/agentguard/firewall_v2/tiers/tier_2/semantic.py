"""Tier 2 placeholder boundary for semantic/retrieval analysis.

The implementation is intentionally conservative until semantic retrieval is calibrated.
It records that Tier 2 was requested and passes uncertainty onward to Tier 3.
"""

from __future__ import annotations

from agentguard.firewall_v2.tiers.models import TierResultV1
from agentguard.intent.models import IntentContractV2
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class Tier2SemanticEvaluator:
    def evaluate(
        self,
        trace: AgentGuardTraceV1,
        intent_contract: IntentContractV2 | None = None,
    ) -> TierResultV1:
        return TierResultV1(
            tier="tier_2",
            status="not_available",
            recommendation="not_available",
            confidence=0.0,
            evidence={
                "trace_id": trace.trace_id,
                "retrieval_text": trace.retrieval_text.model_dump(mode="json"),
                "intent_contract": (
                    intent_contract.model_dump(mode="json")
                    if intent_contract is not None
                    else None
                ),
            },
            escalation_reason="Tier 2 semantic retrieval is not implemented yet.",
            explanation=(
                "Tier 2 was enabled, but semantic/retrieval evaluation is not "
                "implemented. Escalate to Tier 3 if available."
            ),
        )
