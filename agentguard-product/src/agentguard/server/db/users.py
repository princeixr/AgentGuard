"""Database-backed user account utilities."""

from __future__ import annotations

import secrets
import uuid

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from agentguard.server.db.models import UserRecord

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(session: Session, *, email: str, password: str) -> UserRecord:
    email = email.lower().strip()
    existing = session.scalar(select(UserRecord).where(UserRecord.email == email))
    if existing is not None:
        raise ValueError("Email already registered.")
    user = UserRecord(
        user_id=f"usr_{secrets.token_urlsafe(12)}",
        email=email,
        password_hash=_pwd_ctx.hash(password),
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
    if not _pwd_ctx.verify(password, user.password_hash):
        return None
    return user


def get_user_by_id(session: Session, user_id: str) -> UserRecord | None:
    return session.scalar(
        select(UserRecord).where(
            UserRecord.user_id == user_id,
            UserRecord.is_active.is_(True),
        )
    )
