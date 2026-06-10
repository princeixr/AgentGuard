"""Agent-owned MCP connection configuration."""

from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class McpServerConfig:
    id: str
    prefix: str
    enabled: bool
    transport: Literal["stdio", "streamable_http"]
    stdio_command: str | None = None
    stdio_args: tuple[str, ...] = ()
    stdio_env: dict[str, str] = field(default_factory=dict)
    http_url: str | None = None
    http_headers: dict[str, str] = field(default_factory=dict)

    def prefixed_tool_name(self, raw_name: str) -> str:
        return f"{self.prefix}_{raw_name}"

    @property
    def ready(self) -> bool:
        if not self.enabled:
            return False
        return self.transport != "stdio" or shutil.which(self.stdio_command or "") is not None


def load_servers(path: Path) -> list[McpServerConfig]:
    if not path.exists():
        return []
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return [_parse_server(item) for item in raw.get("servers", [])]


def _parse_server(raw: dict[str, Any]) -> McpServerConfig:
    transport = raw["transport"]
    if transport == "stdio":
        stdio = raw["stdio"]
        return McpServerConfig(
            id=raw["id"],
            prefix=raw["prefix"].strip("_"),
            enabled=bool(raw.get("enabled", False)),
            transport="stdio",
            stdio_command=_resolve(stdio["command"]),
            stdio_args=tuple(_resolve(item) for item in stdio.get("args", [])),
            stdio_env={key: _resolve(value) for key, value in stdio.get("env", {}).items()},
        )
    http = raw["streamable_http"]
    return McpServerConfig(
        id=raw["id"],
        prefix=raw["prefix"].strip("_"),
        enabled=bool(raw.get("enabled", False)),
        transport="streamable_http",
        http_url=_resolve(http["url"]),
        http_headers={key: _resolve(value) for key, value in http.get("headers", {}).items()},
    )


def _resolve(value: str) -> str:
    for name, item in os.environ.items():
        value = value.replace(f"${{{name}}}", item)
    return value
