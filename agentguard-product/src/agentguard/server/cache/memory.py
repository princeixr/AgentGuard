"""In-memory cache fallback for single-process local development and tests."""

from __future__ import annotations

import asyncio
import copy
import time
from collections.abc import AsyncIterator
from typing import Any

from agentguard.server.cache.base import CacheHealth


class MemoryCache:
    name = "memory"

    def __init__(self) -> None:
        self._items: dict[str, tuple[Any, float | None]] = {}
        self._channels: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def get_json(self, key: str) -> Any | None:
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            return copy.deepcopy(value)

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else None
        async with self._lock:
            self._items[key] = (copy.deepcopy(value), expires_at)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._items.pop(key, None)

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._channels.get(channel, set()))
        for queue in queues:
            await queue.put(copy.deepcopy(payload))

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._channels.setdefault(channel, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                subscribers = self._channels.get(channel)
                if subscribers is not None:
                    subscribers.discard(queue)
                    if not subscribers:
                        self._channels.pop(channel, None)

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        async with self._lock:
            value, expires_at = self._items.get(key, (0, None))
            if expires_at is not None and expires_at <= time.monotonic():
                value = 0
            count = int(value) + 1
            self._items[key] = (count, time.monotonic() + ttl_seconds)
            return count

    async def health(self) -> CacheHealth:
        return CacheHealth(status="operational", detail="In-memory cache is operational.")
