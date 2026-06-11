"""Server configuration validation."""

from __future__ import annotations

import os
from urllib.parse import urlparse


WEAK_VALUES = {
    "",
    "change-me",
    "changeme",
    "replace-me",
    "dev-agentguard-key",
    "agentguard",
    "password",
}


def env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes", "on"}


def validate_startup_config() -> None:
    if os.environ.get("AGENTGUARD_ENV", "development").lower() != "production":
        return

    errors: list[str] = []
    if not env_bool("AGENTGUARD_REQUIRE_AUTH", "false"):
        errors.append("AGENTGUARD_REQUIRE_AUTH must be true in production.")
    if env_bool("AGENTGUARD_DOCS_ENABLED", "false"):
        errors.append("AGENTGUARD_DOCS_ENABLED must be false in production.")
    _require_strong("AGENTGUARD_API_KEY", errors, minimum_length=24, allow_missing=True)
    _require_strong("AGENTGUARD_API_KEY_PEPPER", errors, minimum_length=24)
    database_url = os.environ.get("AGENTGUARD_DATABASE_URL", "")
    if not database_url:
        errors.append("AGENTGUARD_DATABASE_URL is required in production.")
    elif _url_has_weak_password(database_url):
        errors.append("AGENTGUARD_DATABASE_URL must not use a weak/default password.")
    if env_bool("AGENTGUARD_CACHE_ENABLED", "false"):
        redis_url = os.environ.get("AGENTGUARD_REDIS_URL", "")
        if not redis_url:
            errors.append("AGENTGUARD_REDIS_URL is required when cache is enabled.")
        elif _url_has_weak_password(redis_url):
            errors.append("AGENTGUARD_REDIS_URL must include a strong Redis password.")
    origins = [
        item.strip()
        for item in os.environ.get("AGENTGUARD_WEB_ORIGINS", "").split(",")
        if item.strip()
    ]
    if not origins:
        errors.append("AGENTGUARD_WEB_ORIGINS must be set in production.")
    if any(origin in {"*", "http://localhost:5173", "http://127.0.0.1:5173"} for origin in origins):
        errors.append("AGENTGUARD_WEB_ORIGINS must not use wildcard or localhost in production.")
    if errors:
        raise RuntimeError("Invalid AgentGuard production configuration: " + " ".join(errors))


def _require_strong(
    name: str,
    errors: list[str],
    *,
    minimum_length: int,
    allow_missing: bool = False,
) -> None:
    value = os.environ.get(name, "")
    if allow_missing and not value:
        return
    if len(value) < minimum_length or value.lower() in WEAK_VALUES:
        errors.append(f"{name} must be set to a strong non-default value.")


def _url_has_weak_password(url: str) -> bool:
    parsed = urlparse(url)
    password = parsed.password or ""
    return len(password) < 12 or password.lower() in WEAK_VALUES
