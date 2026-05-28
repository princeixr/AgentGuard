"""Local script bootstrap before the package is installed."""

from pathlib import Path
import sys


def bootstrap() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for path in (repo_root, repo_root / "src"):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)

