"""FastAPI application factory for the AgentGuard product demo."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentguard.api.repositories.elastic import ElasticDashboardRepository
from agentguard.api.repositories.local import LocalDashboardRepository
from agentguard.api.routes import (
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
from agentguard.api.services.live import DemoRuntimeService
from agentguard.api.services.query import DashboardQueryService
from agentguard.api.services.adk_test import GoogleADKTestService
from agentguard.demo import reset_demo_runtime
from agentguard.control_plane.registry import DemoAgentRegistry
from agentguard.storage import AgentGuardElasticStore, load_elastic_config


def create_app(
    data_root: Path | str | None = None,
    fixture_root: Path | str | None = None,
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

    local_repository = LocalDashboardRepository(runtime_root)
    if not local_repository.is_ready() and (fixtures / "v1" / "demo").exists():
        reset_demo_runtime(fixtures, runtime_root)
    repository = local_repository
    elastic_config = load_elastic_config()
    if elastic_config.enabled and elastic_config.is_configured:
        try:
            elastic_repository = ElasticDashboardRepository(
                AgentGuardElasticStore(config=elastic_config)
            )
            elastic_repository.is_ready()
            repository = elastic_repository
        except Exception as exc:
            repository = LocalDashboardRepository(
                runtime_root,
                fallback_reason=f"Elastic unavailable; using local data: {exc}",
            )

    app = FastAPI(
        title="AgentGuard Demo API",
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
    app.state.agent_registry = DemoAgentRegistry()
    app.state.adk_test_service = GoogleADKTestService(repo_root=repo_root)
    app.state.query_service = DashboardQueryService(repository)
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
