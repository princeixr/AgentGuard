"""Reset local runtime demo data from the checked-in fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from agentguard.demo import reset_demo_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path, default=Path("demo/fixtures"))
    parser.add_argument("--runtime-root", type=Path, default=Path("data/demo_runtime"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    destination = reset_demo_runtime(args.fixture_root, args.runtime_root)
    print(f"Reset demo runtime data at {destination}")


if __name__ == "__main__":
    main()
