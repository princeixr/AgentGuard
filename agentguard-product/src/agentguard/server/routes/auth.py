"""User authentication routes: register, login, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from agentguard.server.auth.jwt import create_access_token
from agentguard.server.db.users import create_user, get_user_by_id, verify_user
from agentguard.server.dependencies import require_user_jwt

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    workspace_id: str
    user_id: str
    email: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    workspace_id: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, req: Request) -> TokenResponse:
    session_factory = getattr(req.app.state, "db_session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured.",
        )
    try:
        with session_factory() as session:
            user = create_user(session, email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    token = create_access_token(user_id=user.user_id, workspace_id=user.workspace_id)
    return TokenResponse(
        access_token=token,
        workspace_id=user.workspace_id,
        user_id=user.user_id,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, req: Request) -> TokenResponse:
    session_factory = getattr(req.app.state, "db_session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured.",
        )
    with session_factory() as session:
        user = verify_user(session, email=request.email, password=request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    token = create_access_token(user_id=user.user_id, workspace_id=user.workspace_id)
    return TokenResponse(
        access_token=token,
        workspace_id=user.workspace_id,
        user_id=user.user_id,
        email=user.email,
    )


@router.get("/me", response_model=MeResponse)
def me(req: Request, claims: dict = Depends(require_user_jwt)) -> MeResponse:
    session_factory = getattr(req.app.state, "db_session_factory", None)
    email = ""
    if session_factory is not None:
        with session_factory() as session:
            user = get_user_by_id(session, claims["sub"])
            if user is not None:
                email = user.email
    return MeResponse(
        user_id=claims["sub"],
        email=email,
        workspace_id=claims["wid"],
    )
