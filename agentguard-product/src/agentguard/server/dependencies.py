"""FastAPI dependency accessors."""

from fastapi import Request

from agentguard.control_plane.registry import AgentRegistry
from agentguard.server.services.query import DashboardQueryService
from agentguard.server.services.live import DemoRuntimeService
from agentguard.server.services.agent_live import AgentLiveRuntimeService


def get_query_service(request: Request) -> DashboardQueryService:
    return request.app.state.query_service


def get_demo_runtime(request: Request) -> DemoRuntimeService:
    return request.app.state.demo_runtime


def get_agent_registry(request: Request) -> AgentRegistry:
    return request.app.state.agent_registry


def get_agent_live_runtime(request: Request) -> AgentLiveRuntimeService:
    return request.app.state.agent_live_runtime
