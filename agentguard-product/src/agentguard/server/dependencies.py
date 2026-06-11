"""FastAPI dependency accessors."""

import hmac
import os

import jwt
from fastapi import Header, HTTPException, Request, status

from agentguard.control_plane.registry import AgentRegistry
from agentguard.server.services.query import DashboardQueryService
from agentguard.server.services.live import DemoRuntimeService
from agentguard.server.services.agent_live import AgentLiveRuntimeService
from agentguard.server.services.remote_runtime import RemoteInterceptionService
from agentguard.server.db.api_keys import verify_api_key


def get_query_service(request: Request) -> DashboardQueryService:
    return request.app.state.query_service


def get_demo_runtime(request: Request) -> DemoRuntimeService:
    return request.app.state.demo_runtime


def get_agent_registry(request: Request) -> AgentRegistry:
    return request.app.state.agent_registry


def get_agent_live_runtime(request: Request) -> AgentLiveRuntimeService:
    return request.app.state.agent_live_runtime


def get_remote_runtime(request: Request) -> RemoteInterceptionService:
    return request.app.state.remote_runtime


def require_user_jwt(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    """Validate a user JWT and return the decoded claims dict."""
    from agentguard.server.auth.jwt import decode_access_token

    prefix = "Bearer "
    token = None
    if authorization is not None and authorization.startswith(prefix):
        token = authorization[len(prefix):]
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
    if claims.get("typ") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )
    return claims


def require_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    if os.environ.get("AGENTGUARD_REQUIRE_AUTH", "false").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    expected = os.environ.get("AGENTGUARD_API_KEY")
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if not expected and session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AgentGuard auth is enabled but no API-key backend is configured.",
        )
    prefix = "Bearer "
    token = request.query_params.get("access_token") if _allows_query_token(request) else None
    if token is None and authorization is not None and authorization.startswith(prefix):
        token = authorization[len(prefix):]
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing AgentGuard bearer token.",
        )
    if expected and hmac.compare_digest(token, expected):
        return
    if session_factory is not None:
        try:
            with session_factory() as session:
                if verify_api_key(session, token):
                    return
        except Exception:
            pass
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid AgentGuard bearer token.",
    )


def require_operator_access(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """Allow either a valid user JWT or a valid API key for dashboard operator access."""
    if os.environ.get("AGENTGUARD_DASHBOARD_AUTH_DISABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return

    prefix = "Bearer "
    token = request.query_params.get("access_token") if _allows_query_token(request) else None
    if token is None and authorization is not None and authorization.startswith(prefix):
        token = authorization[len(prefix):]

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    # Try JWT first (user login flow)
    try:
        from agentguard.server.auth.jwt import decode_access_token
        claims = decode_access_token(token)
        if claims.get("typ") == "access":
            return
    except Exception:
        pass

    # Fall back to API key (legacy / agent-as-operator scenario)
    require_api_key(request, authorization)


def get_request_workspace_id(
    request: Request,
    authorization: str | None = Header(default=None),
) -> str | None:
    """Extract workspace_id from the current request's JWT or API key. Returns None if unresolvable."""
    prefix = "Bearer "
    token = request.query_params.get("access_token") if _allows_query_token(request) else None
    if token is None and authorization is not None and authorization.startswith(prefix):
        token = authorization[len(prefix):]
    if token is None:
        return None

    # Try JWT first
    try:
        from agentguard.server.auth.jwt import decode_access_token
        claims = decode_access_token(token)
        if claims.get("typ") == "access":
            return claims.get("wid")
    except Exception:
        pass

    # Try API key DB lookup
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if session_factory is not None:
        try:
            from sqlalchemy import select
            from agentguard.server.db.models import ApiKeyRecord
            key_id = token.split(".", 1)[0]
            with session_factory() as session:
                record = session.scalar(
                    select(ApiKeyRecord).where(ApiKeyRecord.key_id == key_id)
                )
                if record is not None:
                    return record.workspace_id
        except Exception:
            pass

    return None


def _allows_query_token(request: Request) -> bool:
    return request.url.path.endswith("/events/stream")
