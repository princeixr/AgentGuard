"""Ingest canonical OpenClaw AgentGuardTraceV1 JSONL into Elasticsearch."""

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
        help="Canonical AgentGuardTraceV1 JSONL file to ingest.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of traces to ingest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize records without contacting Elastic.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    traces = _load_traces(args.trace_file, limit=args.limit)
    if args.dry_run:
        print(f"Validated {len(traces)} trace(s) from {args.trace_file}")
        for trace in traces[:10]:
            print(
                f"- {trace.trace_id} "
                f"{trace.source.scenario_id} "
                f"step={trace.step_index} "
                f"tool={trace.proposed_tool_call.tool_name}"
            )
        return

    config = load_elastic_config()
    config.require_configured()
    store = AgentGuardElasticStore(config=config)
    result = store.bulk_index_traces(traces)
    print(
        f"Indexed {result.indexed}/{result.attempted} trace(s) into "
        f"{config.indices.traces}"
    )
    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors[:5]:
            print(error)
        raise SystemExit(1)


def _load_traces(path: Path, limit: int | None = None) -> list[AgentGuardTraceV1]:
    records = load_jsonl(path)
    if limit is not None:
        records = records[:limit]
    return [AgentGuardTraceV1.model_validate(record) for record in records]


if __name__ == "__main__":
    main()
