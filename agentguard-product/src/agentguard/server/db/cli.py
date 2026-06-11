"""Database administration CLI helpers."""

from __future__ import annotations

import argparse
import sys

from agentguard.server.db.api_keys import create_api_key
from agentguard.server.db.session import create_session_factory


def create_api_key_command() -> None:
    parser = argparse.ArgumentParser(description="Create an AgentGuard database API key.")
    parser.add_argument("--name", required=True, help="Human-readable key name.")
    parser.add_argument("--workspace-id", default=None, help="Optional workspace scope.")
    parser.add_argument(
        "--scope",
        action="append",
        dest="scopes",
        help="Allowed scope. Can be supplied multiple times.",
    )
    args = parser.parse_args()

    session_factory = create_session_factory()
    if session_factory is None:
        raise SystemExit("Set AGENTGUARD_DATABASE_URL before creating API keys.")
    with session_factory() as session:
        created = create_api_key(
            session,
            name=args.name,
            workspace_id=args.workspace_id,
            scopes=args.scopes,
        )
    print(f"key_id={created.key_id}", file=sys.stderr)
    print(created.token)
