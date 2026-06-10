"""Run the AgentGuard API and frontend development server together."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dashboard_root = repo_root / "apps" / "agentguard_dashboard"
    if not (dashboard_root / "node_modules").exists():
        raise SystemExit(
            "Frontend dependencies are missing. Run `npm install` in "
            "`apps/agentguard_dashboard` first."
        )

    env = os.environ.copy()
    python_path = [str(repo_root / "src"), str(repo_root)]
    if env.get("PYTHONPATH"):
        python_path.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_path)

    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "agentguard.server.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=repo_root,
            env=env,
        ),
        subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1"],
            cwd=dashboard_root,
            env=env,
        ),
    ]

    print("AgentGuard demo: http://127.0.0.1:5173")
    print("API docs:       http://127.0.0.1:8000/api/docs")
    print("Press Ctrl+C to stop both processes.")
    stopping = False

    def stop_processes(*_args) -> None:
        nonlocal stopping
        stopping = True
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGINT, stop_processes)
    signal.signal(signal.SIGTERM, stop_processes)
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.25)
    finally:
        stop_processes()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    failed = [
        process.returncode
        for process in processes
        if process.returncode and not stopping
    ]
    if failed:
        raise SystemExit(f"Demo process exited unexpectedly: {failed}")


if __name__ == "__main__":
    main()
