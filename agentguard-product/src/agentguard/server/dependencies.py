"""FastAPI dependency accessors."""

import hmac
import os

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


def _allows_query_token(request: Request) -> bool:
    return request.url.path.endswith("/events/stream")


def require_operator_access(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    if os.environ.get("AGENTGUARD_DASHBOARD_AUTH_DISABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    return require_api_key(request, authorization)
