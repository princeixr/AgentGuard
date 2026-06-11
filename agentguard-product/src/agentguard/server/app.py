"""FastAPI application factory for the AgentGuard server."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from time import perf_counter, time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentguard.server.cache import create_cache_from_env
from agentguard.server.cache.factory import env_bool, env_int
from agentguard.server.config import validate_startup_config
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
    guard_v2,
    health,
    interception,
    live,
    memory,
    operations,
    scenarios,
    sessions,
)
from agentguard.server.services.live import DemoRuntimeService
from agentguard.server.services.query import DashboardQueryService
from agentguard.server.services.agent_live import AgentLiveRuntimeService
from agentguard.server.services.remote_runtime import RemoteInterceptionService
from agentguard.server.db import create_session_factory
from agentguard.server.db.runtime_store import RuntimeDatabaseStore
from agentguard.demo import reset_demo_runtime
from agentguard.control_plane.registry import AgentRegistry
from agentguard.storage import AgentGuardElasticStore, load_elastic_config
from agentguard.tracing.trace_store import TraceStore


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
    validate_startup_config()
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
    db_session_factory = create_session_factory()
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

    docs_enabled = env_bool("AGENTGUARD_DOCS_ENABLED", "true")
    app = FastAPI(
        title="AgentGuard API",
        version="0.1.0",
        docs_url="/api/docs" if docs_enabled else None,
        openapi_url="/api/openapi.json" if docs_enabled else None,
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

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers["Server-Timing"] = (
            f"app;dur={(perf_counter() - started) * 1000:.2f}"
        )
        return response

    cache = create_cache_from_env()

    @app.middleware("http")
    async def rate_limit_api_requests(request: Request, call_next):
        if not _should_rate_limit(request):
            return await call_next(request)
        limit = env_int("AGENTGUARD_RATE_LIMIT_PER_MINUTE", 300)
        identity = _rate_limit_identity(request)
        cache_key = f"rate_limit:{identity}:{int(time() // 60)}"
        try:
            count = await cache.incr_with_ttl(cache_key, 90)
        except Exception:
            return await call_next(request)
        if count > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "AgentGuard API rate limit exceeded."},
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response

    app.state.repository = repository
    app.state.db_session_factory = db_session_factory
    app.state.cache = cache
    app.state.agent_registry = AgentRegistry()
    app.state.query_service = DashboardQueryService(repository)
    app.state.remote_runtime = RemoteInterceptionService(
        registry=app.state.agent_registry,
        trace_store=TraceStore(root_dir=trace_root),
        namespace=trace_namespace,
        approval_root=repo_root / os.environ.get(
            "AGENTGUARD_APPROVAL_ROOT",
            "data/approvals",
        ),
        database_store=RuntimeDatabaseStore(db_session_factory),
        cache=cache,
    )
    app.state.agent_live_runtime = AgentLiveRuntimeService(
        repository,
        app.state.query_service,
    )
    app.state.demo_runtime = DemoRuntimeService(
        repository,
        app.state.query_service,
        step_delay_seconds=float(os.environ.get("AGENTGUARD_DEMO_STEP_DELAY", "0.35")),
        cache=cache,
    )
    app.state.data_root = runtime_root
    app.state.fixture_root = fixtures

    api = "/api/v1"
    app.include_router(health.router, prefix=api)
    app.include_router(interception.router, prefix=api)
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
    app.include_router(guard_v2.router, prefix="/api/v2")
    return app


app = create_app()


def _should_rate_limit(request: Request) -> bool:
    if not env_bool("AGENTGUARD_RATE_LIMIT_ENABLED", "false"):
        return False
    if request.method == "OPTIONS":
        return False
    if not request.url.path.startswith("/api/"):
        return False
    return request.url.path not in {"/api/v1/health", "/api/v1/metrics"}


def _rate_limit_identity(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        digest = hashlib.sha256(
            authorization.removeprefix("Bearer ").encode("utf-8")
        ).hexdigest()
        return f"token:{digest[:24]}"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"
