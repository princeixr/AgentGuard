"""Health routes."""

import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from agentguard.server.cache.factory import cache_health
from agentguard.server.dependencies import get_query_service
from agentguard.server.db import database_health
from agentguard.server.models import ComponentHealth, HealthResponse
from agentguard.server.services.query import DashboardQueryService

router = APIRouter(tags=["health"])
STARTED_AT = time.time()


@router.get("/health", response_model=HealthResponse)
async def health(
    request: Request,
    service: DashboardQueryService = Depends(get_query_service),
) -> HealthResponse:
    response = service.health()
    status, detail = database_health(
        getattr(request.app.state, "db_session_factory", None)
    )
    cache_status = await cache_health(getattr(request.app.state, "cache", None))
    return response.model_copy(
        update={
            "status": (
                "degraded"
                if status == "unavailable"
                or cache_status.status == "unavailable"
                or response.status == "degraded"
                else "operational"
            ),
            "components": [
                *response.components,
                ComponentHealth(name="Database", status=status, detail=detail),
                ComponentHealth(
                    name="Cache",
                    status=cache_status.status,
                    detail=cache_status.detail,
                ),
            ],
        }
    )


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(request: Request) -> str:
    session_factory = getattr(request.app.state, "db_session_factory", None)
    db_status, _detail = database_health(session_factory)
    db_ready = 1 if db_status == "operational" else 0
    cache = getattr(request.app.state, "cache", None)
    cache_ready = 0 if cache is None else 1
    uptime = max(0.0, time.time() - STARTED_AT)
    return "\n".join(
        [
            "# HELP agentguard_up AgentGuard API process health.",
            "# TYPE agentguard_up gauge",
            "agentguard_up 1",
            "# HELP agentguard_database_up AgentGuard database connectivity.",
            "# TYPE agentguard_database_up gauge",
            f"agentguard_database_up {db_ready}",
            "# HELP agentguard_cache_configured AgentGuard cache configured.",
            "# TYPE agentguard_cache_configured gauge",
            f"agentguard_cache_configured {cache_ready}",
            "# HELP agentguard_process_uptime_seconds AgentGuard process uptime.",
            "# TYPE agentguard_process_uptime_seconds gauge",
            f"agentguard_process_uptime_seconds {uptime:.0f}",
            "",
        ]
    )
