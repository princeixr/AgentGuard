"""Database-backed user account utilities."""

from __future__ import annotations

import hashlib
import secrets
import uuid

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from agentguard.server.db.models import UserRecord

PASSWORD_MIN = 4
PASSWORD_MAX = 40


def _validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN or len(password) > PASSWORD_MAX:
        raise ValueError(
            f"Password must be between {PASSWORD_MIN} and {PASSWORD_MAX} characters."
        )


def _prehash(password: str) -> bytes:
    """SHA-256 digest of the password, returned as raw bytes (32 bytes).

    bcrypt 4+ raises an error for inputs > 72 bytes. SHA-256 output is always
    32 bytes — safely under the limit regardless of the original password length
    or Unicode content.
    """
    return hashlib.sha256(password.encode("utf-8")).digest()


def _hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_prehash(password), bcrypt.gensalt(12))
    return hashed.decode("utf-8")


def _verify_password(password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(_prehash(password), stored_hash.encode("utf-8"))


def create_user(session: Session, *, email: str, password: str) -> UserRecord:
    _validate_password(password)
    email = email.lower().strip()
    existing = session.scalar(select(UserRecord).where(UserRecord.email == email))
    if existing is not None:
        raise ValueError("Email already registered.")
    user = UserRecord(
        user_id=f"usr_{secrets.token_urlsafe(12)}",
        email=email,
        password_hash=_hash_password(password),
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
    if not _verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(session: Session, user_id: str) -> UserRecord | None:
    return session.scalar(
        select(UserRecord).where(
            UserRecord.user_id == user_id,
            UserRecord.is_active.is_(True),
        )
    )
