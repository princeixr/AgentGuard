"""Async cache contracts used by the AgentGuard API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CacheHealth:
    status: str
    detail: str


class AgentGuardCache(Protocol):
    name: str

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | str | int | float | bool | None:
        ...

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        ...

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        ...

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        ...

    async def health(self) -> CacheHealth:
        ...
