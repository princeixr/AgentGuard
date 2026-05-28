"""Trace retrieval abstractions and a simple local lexical retriever."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from pydantic import BaseModel

from agentguard.core.enums import FailureType, Verdict
from agentguard.core.models import RawTraceRecord
from agentguard.tracing.serializers import load_jsonl


class RetrievedTrace(BaseModel):
    trace_id: str
    similarity: float
    verdict: Verdict
    failure_type: FailureType | None = None
    rationale_summary: str | None = None


class RetrievalResult(BaseModel):
    approved: list[RetrievedTrace]
    blocked: list[RetrievedTrace]
    latency_ms: int


class TraceRetriever:
    def __init__(self, seed_memory_dir: str | Path = "data/seed_memory"):
        self.seed_memory_dir = Path(seed_memory_dir)

    def retrieve_similar(self, trace: RawTraceRecord, k: int = 5) -> RetrievalResult:
        started = perf_counter()
        approved = self._load_and_score(self.seed_memory_dir / "approved_traces.jsonl", trace, k)
        blocked = self._load_and_score(self.seed_memory_dir / "blocked_traces.jsonl", trace, k)
        latency_ms = int((perf_counter() - started) * 1000)
        return RetrievalResult(approved=approved, blocked=blocked, latency_ms=latency_ms)

    def _load_and_score(self, path: Path, trace: RawTraceRecord, k: int) -> list[RetrievedTrace]:
        records = load_jsonl(path)
        scored = []
        query = self._trace_text(trace)
        for record in records:
            text = " ".join(str(record.get(field, "")) for field in record)
            similarity = lexical_similarity(query, text)
            scored.append(
                RetrievedTrace(
                    trace_id=str(record.get("trace_id", "unknown")),
                    similarity=similarity,
                    verdict=record.get("verdict", Verdict.ALLOW),
                    failure_type=record.get("failure_type"),
                    rationale_summary=record.get("rationale_summary"),
                )
            )
        return sorted(scored, key=lambda item: item.similarity, reverse=True)[:k]

    def _trace_text(self, trace: RawTraceRecord) -> str:
        prior = " ".join(call.tool_name for call in trace.prior_tool_calls)
        return " ".join(
            [
                trace.domain,
                trace.task_category,
                trace.user_intent.normalized_intent,
                trace.proposed_tool_call.tool_name,
                trace.proposed_tool_call.argument_summary,
                prior,
            ]
        )


def lexical_similarity(left: str, right: str) -> float:
    left_tokens = set(left.lower().replace("_", " ").split())
    right_tokens = set(right.lower().replace("_", " ").split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

