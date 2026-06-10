"""Local script bootstrap before the package is installed."""

import os
from pathlib import Path
import sys


def bootstrap() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for path in (repo_root, repo_root / "src"):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
    load_env_file(repo_root / ".env")
    env_file = os.environ.get("AGENTGUARD_ENV_FILE")
    if env_file:
        load_env_file(repo_root / env_file)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
