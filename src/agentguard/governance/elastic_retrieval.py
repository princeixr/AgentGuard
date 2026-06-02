"""Elastic-backed retrieval provider for AgentGuard v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentguard.governance.retrieval_v1 import RetrievalProviderV1
from agentguard.storage import AgentGuardElasticStore
from agentguard.tracing.schema_v1 import AgentGuardTraceV1, RetrievalFeatureV1


INTERVENTION_DECISIONS = {"review", "require_approval", "block"}
NON_INTERVENTION_DECISIONS = {"allow", "warn"}


@dataclass(frozen=True)
class ElasticRetrievalConfig:
    top_k: int = 8
    include_live: bool = False


class ElasticTraceRetrievalProvider(RetrievalProviderV1):
    def __init__(
        self,
        store: AgentGuardElasticStore,
        config: ElasticRetrievalConfig | None = None,
    ):
        self.store = store
        self.config = config or ElasticRetrievalConfig()

    def retrieve(self, trace: AgentGuardTraceV1) -> RetrievalFeatureV1:
        response = self.store.search_similar_traces(
            trace,
            size=self.config.top_k,
            include_live=self.config.include_live,
        )
        hits = response.get("hits", {}).get("hits", [])
        trace_ids = [_hit_trace_id(hit) for hit in hits]
        trace_ids = [trace_id for trace_id in trace_ids if trace_id]
        scores_by_trace_id = _normalized_scores_by_trace_id(hits)
        decisions = self.store.find_latest_decisions_by_trace_ids(trace_ids)
        labels = self.store.find_labels_by_trace_ids(trace_ids)

        approved_trace_ids: list[str] = []
        blocked_trace_ids: list[str] = []
        approved_scores: list[float] = []
        blocked_scores: list[float] = []

        for trace_id in trace_ids:
            label = labels.get(trace_id)
            decision = decisions.get(trace_id)
            verdict = None
            if label:
                verdict = label.get("gold_verdict")
            if verdict is None and decision:
                verdict = decision.get("decision")

            score = scores_by_trace_id.get(trace_id, 0.0)
            if verdict in INTERVENTION_DECISIONS:
                blocked_trace_ids.append(trace_id)
                blocked_scores.append(score)
            elif verdict in NON_INTERVENTION_DECISIONS:
                approved_trace_ids.append(trace_id)
                approved_scores.append(score)

        labeled_count = len(approved_trace_ids) + len(blocked_trace_ids)
        blocked_neighbor_ratio = len(blocked_trace_ids) / labeled_count if labeled_count else 0.0

        return RetrievalFeatureV1(
            query_text=trace.retrieval_text.summary,
            top_k=len(hits),
            approved_trace_ids=approved_trace_ids,
            blocked_trace_ids=blocked_trace_ids,
            max_approved_similarity=max(approved_scores, default=0.0),
            max_blocked_similarity=max(blocked_scores, default=0.0),
            mean_approved_similarity=_mean(approved_scores),
            mean_blocked_similarity=_mean(blocked_scores),
            blocked_neighbor_ratio=blocked_neighbor_ratio,
        )


def _hit_trace_id(hit: dict[str, Any]) -> str | None:
    source = hit.get("_source", {})
    return source.get("trace_id") or hit.get("_id")


def _normalized_scores_by_trace_id(hits: list[dict[str, Any]]) -> dict[str, float]:
    max_score = max((float(hit.get("_score") or 0.0) for hit in hits), default=0.0)
    if max_score <= 0:
        return {}
    scores = {}
    for hit in hits:
        trace_id = _hit_trace_id(hit)
        if trace_id:
            scores[trace_id] = min(1.0, max(0.0, float(hit.get("_score") or 0.0) / max_score))
    return scores


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
