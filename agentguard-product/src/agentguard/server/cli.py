"""Command-line entry point for the standalone AgentGuard service."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "agentguard.server.app:app",
        host=os.environ.get("AGENTGUARD_SERVER_HOST", "127.0.0.1"),
        port=int(os.environ.get("AGENTGUARD_SERVER_PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
