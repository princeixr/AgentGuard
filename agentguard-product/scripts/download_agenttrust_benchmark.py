"""Download the pinned Apache-licensed AgentTrust benchmark corpus."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

from _bootstrap import bootstrap

bootstrap()

COMMIT = "aee262344315e29b4d0a9e23eb180af9b8193d6b"
RAW_ROOT = f"https://raw.githubusercontent.com/chenglin1112/AgentTrust/{COMMIT}"
SCENARIO_FILES = (
    "code_execution.yaml",
    "credential_exposure.yaml",
    "data_exfiltration.yaml",
    "file_operations.yaml",
    "network_access.yaml",
    "system_config.yaml",
)


def main() -> None:
    destination = (
        Path(__file__).resolve().parents[1] / "benchmarks" / "agenttrust_v0_5_0"
    )
    scenarios = destination / "scenarios"
    scenarios.mkdir(parents=True, exist_ok=True)
    for name in SCENARIO_FILES:
        _download(
            f"{RAW_ROOT}/src/agent_trust/benchmarks/scenarios/{name}",
            scenarios / name,
        )
    _download(
        f"{RAW_ROOT}/src/agent_trust/benchmarks/split.json",
        destination / "split.json",
    )
    _download(f"{RAW_ROOT}/LICENSE", destination / "LICENSE")
    print(f"Downloaded AgentTrust v0.5.0 benchmark to {destination}")


def _download(url: str, destination: Path) -> None:
    with urlopen(url, timeout=30) as response:
        destination.write_bytes(response.read())


if __name__ == "__main__":
    main()
