"""Export Elastic database workspace artifacts under data/elastic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from agentguard.storage.elastic_config import ElasticIndexNames
from agentguard.storage.index_templates import all_index_mappings


DEFAULT_OUTPUT_ROOT = Path("data/elastic")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Elastic workspace root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mappings_dir = args.output_root / "mappings"
    mappings_dir.mkdir(parents=True, exist_ok=True)
    index_names = ElasticIndexNames()
    for index_name, mapping in all_index_mappings(index_names).items():
        path = mappings_dir / f"{index_name}.json"
        path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
