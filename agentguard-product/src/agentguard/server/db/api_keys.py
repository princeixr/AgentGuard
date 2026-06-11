"""Database-backed AgentGuard API key utilities."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentguard.server.db.models import ApiKeyRecord


@dataclass(frozen=True)
class CreatedApiKey:
    key_id: str
    secret: str
    token: str


def create_api_key(
    session: Session,
    *,
    name: str,
    workspace_id: str | None = None,
    scopes: list[str] | None = None,
) -> CreatedApiKey:
    key_id = f"agk_{secrets.token_urlsafe(12)}"
    secret = secrets.token_urlsafe(32)
    token = f"{key_id}.{secret}"
    session.add(
        ApiKeyRecord(
            key_id=key_id,
            name=name,
            workspace_id=workspace_id,
            scopes=scopes or ["runtime:write", "approvals:write", "dashboard:read"],
            key_hash=hash_token(token),
        )
    )
    session.commit()
    return CreatedApiKey(key_id=key_id, secret=secret, token=token)


def verify_api_key(session: Session, token: str) -> bool:
    key_id = token.split(".", 1)[0]
    record = session.scalar(
        select(ApiKeyRecord).where(
            ApiKeyRecord.key_id == key_id,
            ApiKeyRecord.is_active.is_(True),
            ApiKeyRecord.revoked_at.is_(None),
        )
    )
    if record is None:
        return False
    if not hmac.compare_digest(record.key_hash, hash_token(token)):
        return False
    record.last_used_at = datetime.now(timezone.utc)
    session.commit()
    return True


def hash_token(token: str) -> str:
    pepper = os.environ.get("AGENTGUARD_API_KEY_PEPPER", "")
    digest = hashlib.sha256(f"{pepper}:{token}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
