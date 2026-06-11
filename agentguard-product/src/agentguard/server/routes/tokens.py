"""Agent API token management routes (create, list, revoke)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from agentguard.server.db.api_keys import create_api_key
from agentguard.server.db.models import ApiKeyRecord
from agentguard.server.dependencies import require_user_jwt

router = APIRouter(prefix="/tokens", tags=["tokens"])


class CreateTokenRequest(BaseModel):
    name: str


class TokenInfo(BaseModel):
    key_id: str
    name: str
    created_at: datetime
    last_used_at: datetime | None = None


class CreatedTokenResponse(BaseModel):
    key_id: str
    name: str
    token: str
    created_at: datetime


class TokenListResponse(BaseModel):
    items: list[TokenInfo]


@router.post("", response_model=CreatedTokenResponse, status_code=status.HTTP_201_CREATED)
def create_token(
    body: CreateTokenRequest,
    req: Request,
    claims: dict = Depends(require_user_jwt),
) -> CreatedTokenResponse:
    session_factory = getattr(req.app.state, "db_session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured.",
        )
    with session_factory() as session:
        created = create_api_key(
            session,
            name=body.name,
            workspace_id=claims["wid"],
        )
        record = session.scalar(
            select(ApiKeyRecord).where(ApiKeyRecord.key_id == created.key_id)
        )
        record.user_id = claims["sub"]
        session.commit()
        created_at = record.created_at

    return CreatedTokenResponse(
        key_id=created.key_id,
        name=body.name,
        token=created.token,
        created_at=created_at,
    )


@router.get("", response_model=TokenListResponse)
def list_tokens(
    req: Request,
    claims: dict = Depends(require_user_jwt),
) -> TokenListResponse:
    session_factory = getattr(req.app.state, "db_session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured.",
        )
    with session_factory() as session:
        records = session.scalars(
            select(ApiKeyRecord).where(
                ApiKeyRecord.user_id == claims["sub"],
                ApiKeyRecord.is_active.is_(True),
                ApiKeyRecord.revoked_at.is_(None),
            )
        ).all()
        items = [
            TokenInfo(
                key_id=r.key_id,
                name=r.name,
                created_at=r.created_at,
                last_used_at=r.last_used_at,
            )
            for r in records
        ]
    return TokenListResponse(items=items)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    key_id: str,
    req: Request,
    claims: dict = Depends(require_user_jwt),
) -> None:
    session_factory = getattr(req.app.state, "db_session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured.",
        )
    with session_factory() as session:
        record = session.scalar(
            select(ApiKeyRecord).where(
                ApiKeyRecord.key_id == key_id,
                ApiKeyRecord.user_id == claims["sub"],
            )
        )
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")
        from datetime import timezone
        record.revoked_at = datetime.now(timezone.utc)
        record.is_active = False
        session.commit()
