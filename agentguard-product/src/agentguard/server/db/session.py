"""Database engine/session setup."""

from __future__ import annotations

import os
from collections.abc import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


SessionFactory = Callable[[], Session]


def configured_database_url() -> str | None:
    return os.environ.get("AGENTGUARD_DATABASE_URL") or os.environ.get("DATABASE_URL")


def database_enabled() -> bool:
    return bool(configured_database_url())


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session] | None:
    url = database_url or configured_database_url()
    if not url:
        return None
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=int(os.environ.get("AGENTGUARD_DB_POOL_SIZE", "5")),
        max_overflow=int(os.environ.get("AGENTGUARD_DB_MAX_OVERFLOW", "10")),
        future=True,
    )
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def database_health(session_factory: SessionFactory | None) -> tuple[str, str]:
    if session_factory is None:
        return "degraded", "Database is not configured; using local JSONL fallback."
    try:
        with session_factory() as session:
            session.execute(text("select 1"))
        return "operational", "Database connection is healthy."
    except Exception as exc:
        return "unavailable", f"Database connection failed: {exc}"


def engine_from_session_factory(session_factory: sessionmaker[Session]) -> Engine:
    bind = session_factory.kw["bind"]
    if not isinstance(bind, Engine):
        raise TypeError("Expected SQLAlchemy Engine bind.")
    return bind
