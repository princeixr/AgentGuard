"""Replay AgentGuardTraceV1 records through the v1 firewall."""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from agentguard.governance.firewall_v1 import AgentGuardFirewallV1
from agentguard.tracing.schema_v1 import AgentGuardTraceV1
from agentguard.tracing.serializers import load_jsonl
from agentguard.tracing.trace_store import TraceStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-file",
        type=Path,
        default=Path("data/traces/v1/openclaw/traces.jsonl"),
        help="AgentGuardTraceV1 JSONL file to replay.",
    )
    parser.add_argument(
        "--trace-root",
        type=Path,
        default=Path("data/traces"),
        help="Local trace artifact root.",
    )
    parser.add_argument(
        "--namespace",
        default="replay",
        help="Local/Elastic namespace label for output artifacts.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--elastic",
        action="store_true",
        help="Mirror replay artifacts to Elastic using env config.",
    )
    parser.add_argument(
        "--continue-on-elastic-error",
        action="store_true",
        help="Keep replaying if Elastic writes fail.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    traces = _load_traces(args.trace_file, limit=args.limit)
    firewall = AgentGuardFirewallV1(
        trace_store=TraceStore(root_dir=args.trace_root),
        namespace=args.namespace,
        enable_elastic=args.elastic,
        fail_on_elastic_error=not args.continue_on_elastic_error,
    )
    decisions = []
    for trace in traces:
        result = firewall.intercept(trace)
        decisions.append(result.decision)
        print(
            f"{trace.trace_id} "
            f"scenario={trace.source.scenario_id} "
            f"tool={trace.proposed_tool_call.tool_name} "
            f"decision={result.decision.decision} "
            f"risk={result.decision.final_risk_score:.2f}"
        )
    print(f"Replayed {len(decisions)} trace(s).")


def _load_traces(path: Path, limit: int | None = None) -> list[AgentGuardTraceV1]:
    records = load_jsonl(path)
    if limit is not None:
        records = records[:limit]
    return [AgentGuardTraceV1.model_validate(record) for record in records]


if __name__ == "__main__":
    main()
