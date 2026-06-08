"""Declarative MCP server configuration and tool metadata resolution."""

from __future__ import annotations

import os
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from agentguard.core.enums import ToolRiskLevel
from agentguard.runtime.tool_registry import ToolMetadata

_ENV_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_SERVER_KEYS = {"id", "prefix", "enabled", "transport", "stdio", "streamable_http"}
_READ_ACTIONS = {"get", "list", "lookup", "read", "search", "view", "inspect", "fetch", "download"}
_LOW_SIDE_EFFECT_ACTIONS = {"draft", "preview", "stage"}
_WRITE_ACTIONS = {
    "approve",
    "create",
    "dispatch",
    "edit",
    "execute",
    "publish",
    "reply",
    "run",
    "send",
    "trigger",
    "update",
    "upload",
    "write",
}
_IRREVERSIBLE_ACTIONS = {"delete", "destroy", "merge", "purge", "remove", "revoke"}


class McpRegistryError(ValueError):
    """Raised when declarative MCP configuration is invalid."""


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

    def prefixed_tool_name(self, raw_tool_name: str) -> str:
        return f"{self.prefix}_{raw_tool_name}"


@dataclass(frozen=True)
class McpServerStatus:
    id: str
    prefix: str
    transport: str
    enabled: bool
    ready: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prefix": self.prefix,
            "transport": self.transport,
            "enabled": self.enabled,
            "ready": self.ready,
            "detail": self.detail,
        }


class McpRegistry:
    def __init__(
        self,
        servers: list[McpServerConfig],
        source_path: Path | None = None,
        secret_values: tuple[str, ...] = (),
    ):
        self.servers = servers
        self.source_path = source_path
        self.secret_values = secret_values
        self._by_prefix = {server.prefix: server for server in servers}
        self._prefixes_by_length = sorted(self._by_prefix, key=len, reverse=True)
        self._discovered_tools: dict[str, ToolMetadata] = {}

    @classmethod
    def load(cls, path: Path | str) -> "McpRegistry":
        source_path = Path(path)
        if not source_path.exists():
            return cls([], source_path=source_path)
        try:
            with source_path.open("rb") as handle:
                raw = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise McpRegistryError(f"Invalid MCP registry TOML: {exc}") from exc
        servers = [_parse_server(item, index) for index, item in enumerate(raw.get("servers", []))]
        _validate_unique_servers(servers)
        referenced_names = set(_find_env_references(raw))
        secret_values = tuple(
            value
            for name in sorted(referenced_names)
            if (value := os.environ.get(name)) and len(value) >= 4
        )
        return cls(servers, source_path=source_path, secret_values=secret_values)

    def enabled_servers(self) -> list[McpServerConfig]:
        return [server for server in self.servers if server.enabled]

    def ready_servers(self) -> list[McpServerConfig]:
        statuses = {status.id: status for status in self.statuses()}
        return [server for server in self.enabled_servers() if statuses[server.id].ready]

    def statuses(self) -> list[McpServerStatus]:
        return [_server_status(server) for server in self.servers]

    def discovered_tool_names(self, ready_only: bool = False) -> list[str]:
        servers = self.ready_servers() if ready_only else self.servers
        server_ids = {server.id for server in servers}
        return [
            name
            for name, metadata in self._discovered_tools.items()
            if metadata.mcp_server in server_ids
        ]

    def metadata_for(self, tool_name: str) -> ToolMetadata | None:
        server, raw_tool_name = self.resolve_tool(tool_name)
        if server is None or raw_tool_name is None:
            return None
        if tool_name in self._discovered_tools:
            return self._discovered_tools[tool_name]
        return infer_discovered_mcp_metadata(
            tool_name=tool_name,
            server=server,
            raw_tool_name=raw_tool_name,
        )

    def register_discovered_tool(self, server: McpServerConfig, tool: Any) -> ToolMetadata:
        raw_tool = getattr(tool, "_mcp_tool", tool)
        raw_name = str(getattr(raw_tool, "name", None) or getattr(tool, "name", "unknown_tool"))
        tool_name = server.prefixed_tool_name(raw_name)
        metadata = infer_discovered_mcp_metadata(
            tool_name=tool_name,
            server=server,
            raw_tool_name=raw_name,
            description=getattr(raw_tool, "description", None) or getattr(tool, "description", None),
            annotations=getattr(raw_tool, "annotations", None),
        )
        self._discovered_tools[tool_name] = metadata
        return metadata

    def resolve_tool(self, tool_name: str) -> tuple[McpServerConfig | None, str | None]:
        for prefix in self._prefixes_by_length:
            marker = f"{prefix}_"
            if tool_name.startswith(marker):
                return self._by_prefix[prefix], tool_name.removeprefix(marker)
        return None, None

    def redact(self, text: str) -> str:
        redacted = text
        for secret in self.secret_values:
            redacted = redacted.replace(secret, "[REDACTED]")
        return redacted


def _parse_server(raw: Any, index: int) -> McpServerConfig:
    if not isinstance(raw, dict):
        raise McpRegistryError(f"servers[{index}] must be a table.")
    _validate_keys(raw, _SERVER_KEYS, f"servers[{index}]")
    server_id = _required_non_empty_string(raw, "id", index)
    prefix = _required_non_empty_string(raw, "prefix", index).strip("_")
    if not prefix:
        raise McpRegistryError(f"servers[{index}].prefix must be non-empty.")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise McpRegistryError(f"servers[{index}].enabled must be a boolean.")
    transport = raw.get("transport")
    if transport not in {"stdio", "streamable_http"}:
        raise McpRegistryError(
            f"servers[{index}].transport must be 'stdio' or 'streamable_http'."
        )

    if transport == "stdio":
        stdio = _required_table(raw, "stdio", index)
        _validate_keys(stdio, {"command", "args", "env"}, f"servers[{index}].stdio")
        command = _required_non_empty_string(stdio, "command", index, path="stdio")
        args = _string_list(stdio.get("args", []), f"servers[{index}].stdio.args")
        env = _string_map(stdio.get("env", {}), f"servers[{index}].stdio.env")
        return McpServerConfig(
            id=server_id,
            prefix=prefix,
            enabled=enabled,
            transport=transport,
            stdio_command=_resolve_string(command, f"servers[{index}].stdio.command"),
            stdio_args=tuple(
                _resolve_string(value, f"servers[{index}].stdio.args") for value in args
            ),
            stdio_env={
                key: _resolve_string(value, f"servers[{index}].stdio.env.{key}")
                for key, value in env.items()
            },
        )

    http = _required_table(raw, "streamable_http", index)
    _validate_keys(http, {"url", "headers"}, f"servers[{index}].streamable_http")
    url = _required_non_empty_string(http, "url", index, path="streamable_http")
    headers = _string_map(
        http.get("headers", {}), f"servers[{index}].streamable_http.headers"
    )
    return McpServerConfig(
        id=server_id,
        prefix=prefix,
        enabled=enabled,
        transport=transport,
        http_url=_resolve_string(url, f"servers[{index}].streamable_http.url"),
        http_headers={
            key: _resolve_string(value, f"servers[{index}].streamable_http.headers.{key}")
            for key, value in headers.items()
        },
    )

def _server_status(server: McpServerConfig) -> McpServerStatus:
    if not server.enabled:
        return McpServerStatus(server.id, server.prefix, server.transport, False, False, "disabled")
    if server.transport == "stdio":
        command = server.stdio_command or ""
        if shutil.which(command) is None:
            return McpServerStatus(
                server.id,
                server.prefix,
                server.transport,
                True,
                False,
                f"command '{command}' is not available on PATH",
            )
    return McpServerStatus(server.id, server.prefix, server.transport, True, True, "ready")


def _resolve_string(value: str, path: str) -> str:
    missing = sorted({name for name in _ENV_REFERENCE.findall(value) if name not in os.environ})
    if missing:
        raise McpRegistryError(f"{path} references missing environment variable(s): {', '.join(missing)}")
    return _ENV_REFERENCE.sub(lambda match: os.environ[match.group(1)], value)


def _find_env_references(value: Any):
    if isinstance(value, str):
        yield from _ENV_REFERENCE.findall(value)
    elif isinstance(value, list):
        for item in value:
            yield from _find_env_references(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _find_env_references(item)


def _validate_unique_servers(servers: list[McpServerConfig]) -> None:
    ids = [server.id for server in servers]
    prefixes = [server.prefix for server in servers]
    if len(ids) != len(set(ids)):
        raise McpRegistryError("MCP server ids must be unique.")
    if len(prefixes) != len(set(prefixes)):
        raise McpRegistryError("MCP server prefixes must be unique.")


def _required_table(raw: dict[str, Any], key: str, index: int) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise McpRegistryError(f"servers[{index}].{key} must be a table.")
    return value


def _required_non_empty_string(
    raw: dict[str, Any], key: str, index: int, path: str | None = None
) -> str:
    value = raw.get(key)
    location = f"servers[{index}].{path + '.' if path else ''}{key}"
    if not isinstance(value, str) or not value.strip():
        raise McpRegistryError(f"{location} must be a non-empty string.")
    return value.strip()


def _string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise McpRegistryError(f"{path} must be an array of strings.")
    return value


def _string_map(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise McpRegistryError(f"{path} must be a table of string values.")
    return value


def _validate_keys(raw: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise McpRegistryError(f"{path} contains unsupported field(s): {', '.join(unknown)}")


def infer_discovered_mcp_metadata(
    *,
    tool_name: str,
    server: McpServerConfig,
    raw_tool_name: str,
    description: str | None = None,
    annotations: Any = None,
) -> ToolMetadata:
    text = re.sub(r"[_-]+", " ", f"{raw_tool_name} {description or ''}".lower())
    action_tags = tuple(
        action
        for action in sorted(_READ_ACTIONS | _LOW_SIDE_EFFECT_ACTIONS | _WRITE_ACTIONS | _IRREVERSIBLE_ACTIONS)
        if re.search(rf"\b{re.escape(action)}(?:s|ed|ing)?\b", text)
    )
    read_only_hint = getattr(annotations, "readOnlyHint", None)
    destructive_hint = getattr(annotations, "destructiveHint", None)

    if read_only_hint is True:
        risk_level = ToolRiskLevel.READ_ONLY
        requires_confirmation = False
        irreversible = False
        side_effect_type = None
    elif destructive_hint is True or any(tag in _IRREVERSIBLE_ACTIONS for tag in action_tags):
        risk_level = ToolRiskLevel.IRREVERSIBLE
        requires_confirmation = True
        irreversible = True
        side_effect_type = _side_effect_type(action_tags)
    elif any(tag in _LOW_SIDE_EFFECT_ACTIONS for tag in action_tags):
        risk_level = ToolRiskLevel.LOW_SIDE_EFFECT
        requires_confirmation = False
        irreversible = False
        side_effect_type = _side_effect_type(action_tags)
    elif any(tag in _WRITE_ACTIONS for tag in action_tags):
        risk_level = ToolRiskLevel.EXTERNAL_WRITE
        requires_confirmation = True
        irreversible = any(tag in {"publish", "send"} for tag in action_tags)
        side_effect_type = _side_effect_type(action_tags)
    elif any(tag in _READ_ACTIONS for tag in action_tags):
        risk_level = ToolRiskLevel.READ_ONLY
        requires_confirmation = False
        irreversible = False
        side_effect_type = None
    else:
        risk_level = ToolRiskLevel.HIGH_RISK
        requires_confirmation = True
        irreversible = False
        side_effect_type = None

    return ToolMetadata(
        name=tool_name,
        category=_infer_category(server, text),
        risk_level=risk_level,
        side_effect_type=side_effect_type,
        requires_confirmation_by_default=requires_confirmation,
        irreversible=irreversible,
        mcp_server=server.id,
        provider=f"mcp:{server.id}",
        description=description or f"Tool provided by MCP server {server.id}.",
        action_tags=action_tags,
    )


def _infer_category(server: McpServerConfig, text: str) -> str:
    category_terms = {
        "email": ("email", "gmail", "inbox", "message"),
        "code": ("code", "github", "gitlab", "repository", "pull request"),
        "file": ("file", "filesystem", "directory", "attachment"),
        "calendar": ("calendar", "event", "meeting"),
        "database": ("database", "sql", "query", "table"),
        "web": ("browser", "web", "url", "http"),
    }
    server_text = f"{server.id} {server.prefix} {text}".lower()
    return next(
        (
            category
            for category, terms in category_terms.items()
            if any(term in server_text for term in terms)
        ),
        "unknown",
    )


def _side_effect_type(action_tags: tuple[str, ...]) -> str | None:
    if "draft" in action_tags:
        if "delete" in action_tags or "remove" in action_tags:
            return "local_draft_delete"
        return "local_draft_update" if "update" in action_tags else "local_draft_create"
    if "preview" in action_tags:
        return "local_preview"
    if "stage" in action_tags:
        return "local_stage"
    action = next(
        (
            tag
            for tag in action_tags
            if tag in _IRREVERSIBLE_ACTIONS | _WRITE_ACTIONS | _LOW_SIDE_EFFECT_ACTIONS
        ),
        None,
    )
    return f"external_{action}" if action else None
