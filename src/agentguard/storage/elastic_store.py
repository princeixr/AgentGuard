"""Elastic persistence and retrieval for AgentGuard v1 records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

from agentguard.storage.elastic_client import ElasticHttpClient, ElasticHttpError
from agentguard.storage.elastic_config import ElasticConfig, load_elastic_config
from agentguard.storage.index_templates import all_index_mappings
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    GuardDecisionV1,
    GuardScoreV1,
    LabelRecordV1,
    LiveEventV1,
    ScenarioRecordV1,
    SessionRiskStateV1,
    TraceFeatureV1,
)


class BulkIngestResult(BaseModel):
    attempted: int
    indexed: int
    errors: list[dict[str, Any]] = []


class AgentGuardElasticStore:
    def __init__(
        self,
        config: ElasticConfig | None = None,
        client: ElasticHttpClient | None = None,
    ):
        self.config = config or load_elastic_config()
        self.client = client or ElasticHttpClient(self.config)

    def setup_indices(self) -> list[str]:
        created_or_updated = []
        for index_name, mapping in all_index_mappings(self.config.indices).items():
            if self.client.head(index_name):
                self.client.put(f"{index_name}/_mapping", mapping["mappings"])
            else:
                self.client.put(index_name, mapping)
            created_or_updated.append(index_name)
        return created_or_updated

    def ping(self) -> dict[str, Any]:
        return self.client.get("/")

    def index_trace(self, trace: AgentGuardTraceV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.traces, trace.trace_id, trace)

    def index_live_event(self, event: LiveEventV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.live_events, event.event_id, event)

    def index_trace_feature(self, feature: TraceFeatureV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.trace_features, feature.feature_id, feature)

    def index_guard_score(self, score: GuardScoreV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.guard_scores, score.score_id, score)

    def index_guard_decision(self, decision: GuardDecisionV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.guard_decisions, decision.decision_id, decision)

    def index_session_risk(self, state: SessionRiskStateV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.session_risk, state.session_id, state)

    def index_label(self, label: LabelRecordV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.labels, label.label_id, label)

    def index_scenario(self, scenario: ScenarioRecordV1) -> dict[str, Any]:
        return self._index_model(self.config.indices.scenarios, scenario.scenario_id, scenario)

    def bulk_index_traces(self, traces: Iterable[AgentGuardTraceV1]) -> BulkIngestResult:
        lines: list[dict[str, Any]] = []
        attempted = 0
        for trace in traces:
            attempted += 1
            lines.append({"index": {"_index": self.config.indices.traces, "_id": trace.trace_id}})
            lines.append(_model_doc(trace))
        if not lines:
            return BulkIngestResult(attempted=0, indexed=0)

        response = self.client.post_ndjson("_bulk", lines)
        errors = []
        indexed = 0
        for item in response.get("items", []):
            result = item.get("index", {})
            if "error" in result:
                errors.append(result)
            else:
                indexed += 1
        return BulkIngestResult(attempted=attempted, indexed=indexed, errors=errors)

    def get_trace(self, trace_id: str) -> AgentGuardTraceV1 | None:
        try:
            response = self.client.get(f"{self.config.indices.traces}/_doc/{trace_id}")
        except ElasticHttpError as exc:
            if "-> 404:" in str(exc):
                return None
            raise
        source = response.get("_source")
        return AgentGuardTraceV1.model_validate(source) if source else None

    def get_latest_trace(self) -> AgentGuardTraceV1 | None:
        query = {
            "size": 1,
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {"match_all": {}},
        }
        response = self.client.post(f"{self.config.indices.traces}/_search", query)
        hits = response.get("hits", {}).get("hits", [])
        if not hits:
            return None
        return AgentGuardTraceV1.model_validate(hits[0].get("_source", {}))

    def search_similar_traces(
        self,
        trace: AgentGuardTraceV1,
        size: int = 8,
        include_live: bool = False,
    ) -> dict[str, Any]:
        filters: list[dict[str, Any]] = [
            {"term": {"intent.domain": trace.intent.domain}},
            {"term": {"proposed_tool_call.tool_category": trace.proposed_tool_call.tool_category}},
        ]
        if not include_live:
            filters.append({"term": {"source.mode": "historical"}})

        query = {
            "size": size,
            "query": {
                "bool": {
                    "filter": filters,
                    "must": [
                        {
                            "multi_match": {
                                "query": trace.retrieval_text.summary,
                                "fields": [
                                    "retrieval_text.summary^4",
                                    "intent.normalized_intent^3",
                                    "trajectory.prior_tool_sequence^2",
                                    "proposed_tool_call.argument_summary",
                                ],
                            }
                        }
                    ],
                    "must_not": [{"term": {"trace_id": trace.trace_id}}],
                }
            },
        }
        return self.client.post(f"{self.config.indices.traces}/_search", query)

    def find_latest_decisions_by_trace_ids(self, trace_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not trace_ids:
            return {}
        query = {
            "size": max(1, len(trace_ids) * 3),
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {"terms": {"trace_id": trace_ids}},
        }
        response = self.client.post(f"{self.config.indices.guard_decisions}/_search", query)
        decisions: dict[str, dict[str, Any]] = {}
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            trace_id = source.get("trace_id")
            if trace_id and trace_id not in decisions:
                decisions[trace_id] = source
        return decisions

    def find_labels_by_trace_ids(self, trace_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not trace_ids:
            return {}
        query = {
            "size": max(1, len(trace_ids) * 3),
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {"terms": {"trace_id": trace_ids}},
        }
        response = self.client.post(f"{self.config.indices.labels}/_search", query)
        labels: dict[str, dict[str, Any]] = {}
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            trace_id = source.get("trace_id")
            if trace_id and trace_id not in labels:
                labels[trace_id] = source
        return labels

    def _index_model(self, index_name: str, document_id: str, model: BaseModel) -> dict[str, Any]:
        return self.client.put(f"{index_name}/_doc/{document_id}", _model_doc(model))


def _model_doc(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)
