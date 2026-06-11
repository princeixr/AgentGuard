"""Database-backed user account utilities."""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from agentguard.server.db.models import UserRecord

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD_MIN = 4
PASSWORD_MAX = 40


def _validate_password(password: str) -> None:
    length = len(password)
    if length < PASSWORD_MIN or length > PASSWORD_MAX:
        raise ValueError(
            f"Password must be between {PASSWORD_MIN} and {PASSWORD_MAX} characters."
        )


def _prehash(password: str) -> str:
    """SHA-256 prehash before bcrypt to eliminate the 72-byte silent truncation.

    bcrypt silently ignores bytes beyond the 72nd, making passwords that differ
    only after byte 72 hash to the same value. Prehashing with SHA-256 produces
    a fixed 44-character base64 string, safely within bcrypt's limit regardless
    of the original password's length or encoding.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def create_user(session: Session, *, email: str, password: str) -> UserRecord:
    _validate_password(password)
    email = email.lower().strip()
    existing = session.scalar(select(UserRecord).where(UserRecord.email == email))
    if existing is not None:
        raise ValueError("Email already registered.")
    user = UserRecord(
        user_id=f"usr_{secrets.token_urlsafe(12)}",
        email=email,
        password_hash=_pwd_ctx.hash(_prehash(password)),
        workspace_id=str(uuid.uuid4()),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def verify_user(session: Session, *, email: str, password: str) -> UserRecord | None:
    email = email.lower().strip()
    user = session.scalar(
        select(UserRecord).where(
            UserRecord.email == email,
            UserRecord.is_active.is_(True),
        )
    )
    if user is None:
        return None
    if not _pwd_ctx.verify(_prehash(password), user.password_hash):
        return None
    return user


def get_user_by_id(session: Session, user_id: str) -> UserRecord | None:
    return session.scalar(
        select(UserRecord).where(
            UserRecord.user_id == user_id,
            UserRecord.is_active.is_(True),
        )
    )
