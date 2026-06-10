"""FastAPI application factory for the AgentGuard server."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentguard.server.repositories.elastic import ElasticDashboardRepository
from agentguard.server.repositories.local import LocalDashboardRepository
from agentguard.server.repositories.merged import MergedDashboardRepository
from agentguard.server.repositories.runtime import RuntimeFirstDashboardRepository
from agentguard.server.routes import (
    agent_dashboard,
    agent_live,
    agents,
    approvals,
    demo,
    health,
    live,
    memory,
    operations,
    scenarios,
    sessions,
)
from agentguard.server.services.live import DemoRuntimeService
from agentguard.server.services.query import DashboardQueryService
from agentguard.server.services.agent_live import AgentLiveRuntimeService
from agentguard.demo import reset_demo_runtime
from agentguard.control_plane.registry import AgentRegistry
from agentguard.storage import AgentGuardElasticStore, load_elastic_config


def create_app(
    data_root: Path | str | None = None,
    fixture_root: Path | str | None = None,
    agent_trace_root: Path | str | None = None,
) -> FastAPI:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        from dotenv import load_dotenv

        load_dotenv(repo_root / ".env")
    except ModuleNotFoundError:
        pass
    runtime_root = Path(
        data_root or os.environ.get("AGENTGUARD_DEMO_DATA_ROOT", "data/demo_runtime")
    )
    fixtures = Path(
        fixture_root or os.environ.get("AGENTGUARD_DEMO_FIXTURE_ROOT", "demo/fixtures")
    )
    if not runtime_root.is_absolute():
        runtime_root = repo_root / runtime_root
    if not fixtures.is_absolute():
        fixtures = repo_root / fixtures

    demo_repository = LocalDashboardRepository(runtime_root)
    if not demo_repository.is_ready() and (fixtures / "v1" / "demo").exists():
        reset_demo_runtime(fixtures, runtime_root)
    trace_root = Path(
        agent_trace_root
        or (
            Path(data_root).parent / "agent_traces"
            if data_root is not None
            else os.environ.get("AGENTGUARD_TRACE_ROOT", "data/traces")
        )
    )
    if not trace_root.is_absolute():
        trace_root = repo_root / trace_root
    trace_namespace = os.environ.get(
        "AGENTGUARD_TRACE_NAMESPACE", "registered_agents"
    )
    live_repository = MergedDashboardRepository(
        [LocalDashboardRepository(trace_root, namespace=trace_namespace)]
    )
    repository = RuntimeFirstDashboardRepository(
        runtime=live_repository,
        fallback=demo_repository,
    )
    elastic_config = load_elastic_config()
    if elastic_config.enabled and elastic_config.is_configured:
        try:
            elastic_repository = ElasticDashboardRepository(
                AgentGuardElasticStore(config=elastic_config)
            )
            elastic_repository.is_ready()
            repository = elastic_repository
        except Exception as exc:
            repository = RuntimeFirstDashboardRepository(
                runtime=live_repository,
                fallback=demo_repository,
            )
            repository.fallback_reason = (
                f"Elastic unavailable; using local data: {exc}"
            )

    app = FastAPI(
        title="AgentGuard API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in os.environ.get(
                "AGENTGUARD_WEB_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.repository = repository
    app.state.agent_registry = AgentRegistry()
    app.state.query_service = DashboardQueryService(repository)
    app.state.agent_live_runtime = AgentLiveRuntimeService(
        repository,
        app.state.query_service,
    )
    app.state.demo_runtime = DemoRuntimeService(
        repository,
        app.state.query_service,
        step_delay_seconds=float(os.environ.get("AGENTGUARD_DEMO_STEP_DELAY", "0.35")),
    )
    app.state.data_root = runtime_root
    app.state.fixture_root = fixtures

    api = "/api/v1"
    app.include_router(health.router, prefix=api)
    app.include_router(agents.router, prefix=api)
    app.include_router(agent_dashboard.router, prefix=api)
    app.include_router(agent_live.router, prefix=api)
    app.include_router(live.router, prefix=api)
    app.include_router(sessions.router, prefix=api)
    app.include_router(memory.router, prefix=api)
    app.include_router(operations.router, prefix=api)
    app.include_router(scenarios.router, prefix=api)
    app.include_router(demo.router, prefix=api)
    app.include_router(approvals.router, prefix=api)
    return app


app = create_app()
