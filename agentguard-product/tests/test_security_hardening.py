from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentguard.server.app import create_app
from agentguard.server.config import validate_startup_config


def test_query_token_is_rejected_for_non_sse_routes(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTGUARD_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "true")
    monkeypatch.setenv("AGENTGUARD_API_KEY", "test-key")
    client = TestClient(create_app(data_root=tmp_path / "runtime"))

    response = client.get("/api/v1/agents?access_token=test-key")

    assert response.status_code == 401


def test_auth_enabled_without_backend_fails_closed(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTGUARD_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTGUARD_API_KEY", "")
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "true")
    client = TestClient(create_app(data_root=tmp_path / "runtime"))

    response = client.get("/api/v1/agents")

    assert response.status_code == 503


def test_production_rejects_weak_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTGUARD_ENV", "production")
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "true")
    monkeypatch.setenv("AGENTGUARD_DOCS_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_API_KEY", "dev-agentguard-key")
    monkeypatch.setenv("AGENTGUARD_API_KEY_PEPPER", "change-me")
    monkeypatch.setenv(
        "AGENTGUARD_DATABASE_URL",
        "postgresql+psycopg://agentguard:agentguard@postgres:5432/agentguard",
    )
    monkeypatch.setenv("AGENTGUARD_CACHE_ENABLED", "true")
    monkeypatch.setenv("AGENTGUARD_REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("AGENTGUARD_WEB_ORIGINS", "http://localhost:5173")

    with pytest.raises(RuntimeError, match="Invalid AgentGuard production configuration"):
        create_app(data_root=tmp_path / "runtime")


def test_production_accepts_strong_runtime_config(monkeypatch):
    monkeypatch.setenv("AGENTGUARD_ENV", "production")
    monkeypatch.setenv("AGENTGUARD_REQUIRE_AUTH", "true")
    monkeypatch.setenv("AGENTGUARD_DOCS_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_API_KEY", "prod-api-key-strong-value-123456")
    monkeypatch.setenv("AGENTGUARD_API_KEY_PEPPER", "prod-pepper-strong-value-123456")
    monkeypatch.setenv(
        "AGENTGUARD_DATABASE_URL",
        "postgresql+psycopg://agentguard:prod-postgres-password-123456@postgres:5432/agentguard",
    )
    monkeypatch.setenv("AGENTGUARD_CACHE_ENABLED", "true")
    monkeypatch.setenv(
        "AGENTGUARD_REDIS_URL",
        "redis://:prod-redis-password-123456@redis:6379/0",
    )
    monkeypatch.setenv("AGENTGUARD_WEB_ORIGINS", "https://agentguard.example.com")

    validate_startup_config()
