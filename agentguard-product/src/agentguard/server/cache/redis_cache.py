"""Redis cache backend for distributed AgentGuard deployments."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from agentguard.server.cache.base import CacheHealth


class RedisCache:
    name = "redis"

    def __init__(self, url: str) -> None:
        try:
            from redis import asyncio as redis_asyncio
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install the redis package to enable Redis caching.") from exc
        self._client = redis_asyncio.from_url(url, decode_responses=True)

    async def get_json(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        raw = json.dumps(value, separators=(",", ":"), default=str)
        if ttl_seconds:
            await self._client.set(key, raw, ex=ttl_seconds)
        else:
            await self._client.set(key, raw)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, separators=(",", ":"), default=str)
        await self._client.publish(channel, raw)

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds, nx=True)
            result = await pipe.execute()
        return int(result[0])

    async def health(self) -> CacheHealth:
        try:
            pong = await self._client.ping()
        except Exception as exc:
            return CacheHealth(status="unavailable", detail=f"Redis unavailable: {exc}")
        if pong:
            return CacheHealth(status="operational", detail="Redis cache is operational.")
        return CacheHealth(status="unavailable", detail="Redis ping failed.")
