"""Query similar traces from Elasticsearch for a canonical trace.

If the local trace file is empty, the script uses the latest trace already indexed in
Elastic as the query seed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from agentguard.storage import AgentGuardElasticStore, load_elastic_config
from agentguard.tracing.schema_v1 import AgentGuardTraceV1
from agentguard.tracing.serializers import load_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-file",
        type=Path,
        default=Path("data/traces/v1/openclaw/traces.jsonl"),
        help="Optional local trace JSONL containing the query trace.",
    )
    parser.add_argument(
        "--trace-id",
        help="Trace ID to use as the query. Defaults to the last trace in the file.",
    )
    parser.add_argument("--size", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_elastic_config()
    config.require_configured()
    store = AgentGuardElasticStore(config=config)
    trace = _select_trace(args.trace_file, args.trace_id, store)
    response = store.search_similar_traces(trace, size=args.size)
    hits = response.get("hits", {}).get("hits", [])
    print(
        f"Query trace: {trace.trace_id} "
        f"{trace.intent.domain}/{trace.proposed_tool_call.tool_name}"
    )
    print(f"Hits: {len(hits)}")
    for hit in hits:
        source = hit.get("_source", {})
        print(
            f"- score={hit.get('_score')} "
            f"trace={source.get('trace_id')} "
            f"scenario={source.get('source', {}).get('scenario_id')} "
            f"tool={source.get('proposed_tool_call', {}).get('tool_name')}"
        )


def _select_trace(
    path: Path,
    trace_id: str | None,
    store: AgentGuardElasticStore,
) -> AgentGuardTraceV1:
    records = [AgentGuardTraceV1.model_validate(record) for record in load_jsonl(path)]
    if trace_id is None and records:
        return records[-1]
    if trace_id is not None:
        for record in records:
            if record.trace_id == trace_id:
                return record
        elastic_trace = store.get_trace(trace_id)
        if elastic_trace is not None:
            return elastic_trace
        raise ValueError(f"Trace ID not found locally or in Elastic: {trace_id}")

    elastic_trace = store.get_latest_trace()
    if elastic_trace is not None:
        print(f"No local traces found in {path}; using latest trace from Elastic.")
        return elastic_trace

    raise ValueError(f"No traces found in {path} or {store.config.indices.traces}")


if __name__ == "__main__":
    main()
