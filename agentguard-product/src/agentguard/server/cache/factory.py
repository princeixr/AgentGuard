"""Cache backend factory."""

from __future__ import annotations

import os

from agentguard.server.cache.base import AgentGuardCache, CacheHealth
from agentguard.server.cache.memory import MemoryCache


def env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def create_cache_from_env() -> AgentGuardCache:
    if not env_bool("AGENTGUARD_CACHE_ENABLED", "false"):
        return MemoryCache()
    redis_url = os.environ.get("AGENTGUARD_REDIS_URL")
    if not redis_url:
        return MemoryCache()
    try:
        from agentguard.server.cache.redis_cache import RedisCache

        return RedisCache(redis_url)
    except Exception:
        return MemoryCache()


async def cache_health(cache: AgentGuardCache | None) -> CacheHealth:
    if cache is None:
        return CacheHealth(status="disabled", detail="Cache is not configured.")
    return await cache.health()
