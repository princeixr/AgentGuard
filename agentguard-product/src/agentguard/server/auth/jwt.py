"""JWT utilities for user session authentication."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_HOURS = 24


def _secret() -> str:
    secret = os.environ.get("AGENTGUARD_JWT_SECRET", "")
    if not secret:
        raise RuntimeError(
            "AGENTGUARD_JWT_SECRET is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret


def create_access_token(*, user_id: str, workspace_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "wid": workspace_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "typ": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
