"""Run the pinned AgentTrust corpus through AgentGuard FirewallV2."""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from agentguard.evaluation.agenttrust_benchmark import (  # noqa: E402
    run_agenttrust_benchmark,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("all", "dev", "test"), default="all")
    parser.add_argument(
        "--scope",
        choices=("shell", "all"),
        default="shell",
        help=(
            "shell evaluates only shell-compatible upstream tools; all also projects "
            "non-shell tools through AgentGuard's shell path."
        ),
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--benchmark-compatibility-rules",
        action="store_true",
        help=(
            "Enable AgentTrust's benchmark-only compatibility rules. "
            "This does not represent the production AgentGuard configuration."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/agenttrust_benchmark.json"),
    )
    args = parser.parse_args()
    dataset_root = (
        Path(__file__).resolve().parents[1] / "benchmarks" / "agenttrust_v0_5_0"
    )
    summary = run_agenttrust_benchmark(
        dataset_root,
        split=args.split,
        scope=args.scope,
        benchmark_compatibility_rules=args.benchmark_compatibility_rules,
        limit=args.limit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        summary.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"cases={summary.total} "
        f"scope={summary.scope} "
        f"agenttrust_verdict_accuracy={summary.agenttrust_verdict_accuracy:.1%} "
        f"agentguard_final_accuracy={summary.exact_accuracy:.1%} "
        f"safety_accuracy={summary.safety_accuracy:.1%} "
        f"risk_accuracy={summary.risk_accuracy:.1%} "
        f"dangerous_false_allows={summary.dangerous_false_allows} "
        f"avg_latency_ms={summary.average_latency_ms:.2f}"
    )
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
