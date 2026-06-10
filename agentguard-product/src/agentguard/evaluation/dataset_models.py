"""Benchmark dataset models derived from the AgentGuard v1 schema.

AgentGuardTraceV1 is the central trace object. These wrappers add benchmark provenance,
manifest, and split metadata without contaminating traces with labels or guard outputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from agentguard.core.models import AgentGuardModel, utc_now
from agentguard.tracing.schema_v1 import AgentGuardTraceV1


class TraceSourceProvenance(AgentGuardModel):
    source_framework: str
    source_type: str
    source_run_id: str | None = None
    source_session_id: str | None = None
    source_event_id: str | None = None
    source_tool_call_id: str | None = None
    source_transcript_path: str | None = None
    source_record_index: int | None = None
    agent_config_id: str | None = None
    scenario_id: str | None = None
    run_index: int | None = None


class BenchmarkTraceRecord(AgentGuardModel):
    trace: AgentGuardTraceV1
    provenance: TraceSourceProvenance
    dataset_version: str = "intenttracebench_v0"
    created_at: datetime = Field(default_factory=utc_now)


class DatasetSplitEntry(AgentGuardModel):
    trace_id: str
    session_id: str
    scenario_id: str | None = None
    split: Literal["memory_train", "validation", "test", "unseen_agent", "unseen_domain"]
    reason: str | None = None


class DatasetManifest(AgentGuardModel):
    dataset_name: str = "IntentTraceBench"
    dataset_version: str = "intenttracebench_v0"
    raw_trace_count: int = 0
    labeled_trace_count: int = 0
    session_count: int = 0
    agent_frameworks: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    split_files: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=utc_now)
