"""Generate checked-in deterministic artifacts for the AgentGuard product demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from agentguard.demo import generate_demo_fixtures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("demo/fixtures"),
        help="Root that will contain v1/demo fixture artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = generate_demo_fixtures(args.output_root)
    rendered = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    print(f"Generated deterministic demo fixtures at {args.output_root}: {rendered}")


if __name__ == "__main__":
    main()
