"""FastAPI dependency accessors."""

import os

from fastapi import Header, HTTPException, Request, status

from agentguard.control_plane.registry import AgentRegistry
from agentguard.server.services.query import DashboardQueryService
from agentguard.server.services.live import DemoRuntimeService
from agentguard.server.services.agent_live import AgentLiveRuntimeService
from agentguard.server.services.remote_runtime import RemoteInterceptionService


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


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = os.environ.get("AGENTGUARD_API_KEY")
    if not expected:
        return
    prefix = "Bearer "
    if authorization is None or not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing AgentGuard bearer token.",
        )
    token = authorization[len(prefix):]
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid AgentGuard bearer token.",
        )
