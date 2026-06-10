"""Retrieval provider interfaces for AgentGuard v1 feature building."""

from __future__ import annotations

from typing import Protocol

from agentguard.tracing.schema_v1 import AgentGuardTraceV1, RetrievalFeatureV1


class RetrievalProviderV1(Protocol):
    def retrieve(self, trace: AgentGuardTraceV1) -> RetrievalFeatureV1:
        """Return retrieval evidence for a trace."""


class NullRetrievalProviderV1:
    def retrieve(self, trace: AgentGuardTraceV1) -> RetrievalFeatureV1:
        return RetrievalFeatureV1(
            query_text=trace.retrieval_text.summary,
            top_k=0,
        )
