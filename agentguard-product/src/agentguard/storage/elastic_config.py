"""Elastic connection and index configuration."""

from __future__ import annotations

import os
from pydantic import BaseModel, Field


class ElasticIndexNames(BaseModel):
    traces: str = "agentguard-traces-v1"
    live_events: str = "agentguard-live-events-v1"
    trace_features: str = "agentguard-trace-features-v1"
    guard_scores: str = "agentguard-guard-scores-v1"
    guard_decisions: str = "agentguard-guard-decisions-v1"
    session_risk: str = "agentguard-session-risk-v1"
    labels: str = "agentguard-labels-v1"
    scenarios: str = "agentguard-scenarios-v1"


class ElasticConfig(BaseModel):
    enabled: bool = False
    url: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    request_timeout_seconds: int = 30
    indices: ElasticIndexNames = Field(default_factory=ElasticIndexNames)

    @property
    def is_configured(self) -> bool:
        return bool(self.url and (self.api_key or (self.username and self.password)))

    def require_configured(self) -> None:
        if not self.url:
            raise ValueError("Missing ELASTICSEARCH_URL.")
        if not (self.api_key or (self.username and self.password)):
            raise ValueError(
                "Missing Elastic auth. Set ELASTICSEARCH_API_KEY or "
                "ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD."
            )


def load_elastic_config() -> ElasticConfig:
    return ElasticConfig(
        enabled=_env_bool("AGENTGUARD_ELASTIC_ENABLED", default=False),
        url=os.environ.get("ELASTICSEARCH_URL"),
        api_key=os.environ.get("ELASTICSEARCH_API_KEY"),
        username=os.environ.get("ELASTICSEARCH_USERNAME"),
        password=os.environ.get("ELASTICSEARCH_PASSWORD"),
        request_timeout_seconds=int(os.environ.get("ELASTICSEARCH_TIMEOUT_SECONDS", "30")),
        indices=ElasticIndexNames(
            traces=os.environ.get("AGENTGUARD_ELASTIC_TRACES_INDEX", "agentguard-traces-v1"),
            live_events=os.environ.get(
                "AGENTGUARD_ELASTIC_LIVE_EVENTS_INDEX",
                "agentguard-live-events-v1",
            ),
            trace_features=os.environ.get(
                "AGENTGUARD_ELASTIC_TRACE_FEATURES_INDEX",
                "agentguard-trace-features-v1",
            ),
            guard_scores=os.environ.get(
                "AGENTGUARD_ELASTIC_GUARD_SCORES_INDEX",
                "agentguard-guard-scores-v1",
            ),
            guard_decisions=os.environ.get(
                "AGENTGUARD_ELASTIC_GUARD_DECISIONS_INDEX",
                "agentguard-guard-decisions-v1",
            ),
            session_risk=os.environ.get(
                "AGENTGUARD_ELASTIC_SESSION_RISK_INDEX",
                "agentguard-session-risk-v1",
            ),
            labels=os.environ.get("AGENTGUARD_ELASTIC_LABELS_INDEX", "agentguard-labels-v1"),
            scenarios=os.environ.get(
                "AGENTGUARD_ELASTIC_SCENARIOS_INDEX",
                "agentguard-scenarios-v1",
            ),
        ),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
