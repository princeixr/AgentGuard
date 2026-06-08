"""FastAPI dependency accessors."""

from fastapi import Request

from agentguard.control_plane.registry import DemoAgentRegistry
from agentguard.api.services.query import DashboardQueryService
from agentguard.api.services.live import DemoRuntimeService
from agentguard.api.services.adk_test import GoogleADKTestService
from agentguard.api.services.agent_live import AgentLiveRuntimeService


def get_query_service(request: Request) -> DashboardQueryService:
    return request.app.state.query_service


def get_demo_runtime(request: Request) -> DemoRuntimeService:
    return request.app.state.demo_runtime


def get_agent_registry(request: Request) -> DemoAgentRegistry:
    return request.app.state.agent_registry


def get_adk_test_service(request: Request) -> GoogleADKTestService:
    return request.app.state.adk_test_service


def get_agent_live_runtime(request: Request) -> AgentLiveRuntimeService:
    return request.app.state.agent_live_runtime
