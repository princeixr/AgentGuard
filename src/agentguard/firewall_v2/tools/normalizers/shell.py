"""Conservative normalizer for the demo shell tool."""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from urllib.parse import urlparse

from agentguard.firewall_v2.tools.normalizers.models import (
    NormalizedActionV1,
    NormalizedDestinationV1,
    NormalizedResourceV1,
    ParserResultV1,
)
from agentguard.tracing.schema_v1 import AgentGuardTraceV1

INSPECT_COMMANDS = {"pwd", "ls", "stat", "file", "du", "df", "find"}
READ_COMMANDS = {"cat", "head", "tail", "less", "more", "wc"}
WRITE_COMMANDS = {"touch", "mkdir", "cp", "mv", "chmod", "chown", "tee"}
DELETE_COMMANDS = {"rm", "rmdir", "unlink", "shred"}
NETWORK_COMMANDS = {"curl", "wget", "ssh", "scp", "sftp", "nc", "ncat", "telnet"}
PRIVILEGE_COMMANDS = {"sudo", "su", "doas"}
PACKAGE_COMMANDS = {
    "apt",
    "apt-get",
    "brew",
    "dnf",
    "gem",
    "npm",
    "pip",
    "pip3",
    "pnpm",
    "uv",
    "yarn",
}
PROCESS_COMMANDS = {
    "kill",
    "killall",
    "pkill",
    "launchctl",
    "systemctl",
    "service",
}
EXECUTE_COMMANDS = {
    "bash",
    "sh",
    "zsh",
    "python",
    "python3",
    "node",
    "ruby",
}
SENSITIVE_PREFIXES = (
    "~/.ssh",
    "~/.aws",
    "~/.config/gcloud",
    "~/Library/Keychains",
    "/etc",
)
CONTROL_PATTERNS = (
    ("command_substitution", re.compile(r"\$\(|`")),
    ("pipeline", re.compile(r"(?<!\|)\|(?!\|)")),
    ("compound_command", re.compile(r"&&|\|\||;")),
)
REDIRECTION_PATTERN = re.compile(r"(?<![<>&])(?:>>|>|<)(?![<>&])")


class ShellNormalizerV1:
    name = "shell_v1"
    version = "1.0.0"

    def normalize(self, trace: AgentGuardTraceV1) -> NormalizedActionV1:
        command = trace.proposed_tool_call.arguments.get("command")
        if not isinstance(command, str) or not command.strip():
            return self._fallback(
                trace,
                status="invalid",
                detail="Shell argument 'command' is missing or empty.",
                flags=["invalid_arguments"],
            )

        syntax_flags = [
            flag for flag, pattern in CONTROL_PATTERNS if pattern.search(command)
        ]
        if syntax_flags:
            return self._fallback(
                trace,
                status="unsupported",
                detail=(
                    "Compound shell syntax is not safely modeled by shell_v1: "
                    + ", ".join(syntax_flags)
                ),
                flags=[*syntax_flags, "unknown_or_unsupported"],
            )

        has_redirection = bool(REDIRECTION_PATTERN.search(command))
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError as exc:
            return self._fallback(
                trace,
                status="invalid",
                detail=f"Shell tokenization failed: {exc}",
                flags=["malformed_shell", "unknown_or_unsupported"],
            )
        if not tokens:
            return self._fallback(
                trace,
                status="invalid",
                detail="Shell command produced no tokens.",
                flags=["invalid_arguments"],
            )

        command_name = Path(tokens[0]).name
        arguments = tokens[1:]
        flags: list[str] = []
        if has_redirection:
            flags.append("redirection")

        if command_name in PRIVILEGE_COMMANDS:
            return self._action(
                trace,
                command,
                operation="privilege_escalation",
                capabilities=["system.privilege_escalate"],
                arguments=arguments,
                resources=[],
                flags=[*flags, "privilege_escalation", "high_impact"],
                side_effect=True,
                reversible=False,
                impact="high",
            )
        if command_name in NETWORK_COMMANDS:
            return self._action(
                trace,
                command,
                operation="network_request",
                capabilities=["shell.network_request"],
                arguments=arguments,
                resources=[],
                destinations=_network_destinations(arguments),
                flags=[*flags, "network_request", "external_effect"],
                side_effect=True,
                reversible=False,
                impact="high",
            )
        if command_name in DELETE_COMMANDS:
            return self._action(
                trace,
                command,
                operation="delete",
                capabilities=["filesystem.delete"],
                arguments=arguments,
                flags=[*flags, "destructive"],
                side_effect=True,
                reversible=False,
                impact="high",
            )
        if command_name in PACKAGE_COMMANDS and _is_package_install(command_name, arguments):
            return self._action(
                trace,
                command,
                operation="package_installation",
                capabilities=["system.package_install"],
                arguments=arguments,
                resources=[],
                flags=[*flags, "package_installation", "system_change"],
                side_effect=True,
                reversible=False,
                impact="high",
            )
        if command_name in PROCESS_COMMANDS:
            return self._action(
                trace,
                command,
                operation="process_control",
                capabilities=["system.process_control"],
                arguments=arguments,
                resources=[],
                flags=[*flags, "process_control"],
                side_effect=True,
                reversible=None,
                impact="high",
            )
        if command_name in INSPECT_COMMANDS:
            return self._action(
                trace,
                command,
                operation="inspect",
                capabilities=["filesystem.inspect"],
                arguments=arguments,
                flags=flags,
                side_effect=False,
                reversible=True,
                impact="low",
            )
        if command_name in READ_COMMANDS:
            return self._action(
                trace,
                command,
                operation="read",
                capabilities=["filesystem.read"],
                arguments=arguments,
                flags=flags,
                side_effect=False,
                reversible=True,
                impact="low",
            )
        if command_name in WRITE_COMMANDS or has_redirection:
            resources = _path_resources(
                _redirection_targets(tokens) if has_redirection else arguments,
                "write",
            )
            return self._action(
                trace,
                command,
                operation="write",
                capabilities=["filesystem.write"],
                arguments=[],
                resources=resources,
                flags=[*flags, "filesystem_change"],
                side_effect=True,
                reversible=True,
                impact="medium",
                confidence=0.9 if has_redirection else 1.0,
            )
        if command_name in EXECUTE_COMMANDS or command.startswith("./"):
            return self._action(
                trace,
                command,
                operation="execute",
                capabilities=["process.execute"],
                arguments=arguments,
                flags=[*flags, "code_execution"],
                side_effect=True,
                reversible=None,
                impact="high",
                confidence=0.85,
            )

        return self._fallback(
            trace,
            status="unsupported",
            detail=f"Command {command_name!r} is not supported by shell_v1.",
            flags=[*flags, "unknown_behavior", "unknown_or_unsupported"],
        )

    def _action(
        self,
        trace: AgentGuardTraceV1,
        raw_command: str,
        *,
        operation: str,
        capabilities: list[str],
        arguments: list[str],
        flags: list[str],
        side_effect: bool,
        reversible: bool | None,
        impact: str,
        resources: list[NormalizedResourceV1] | None = None,
        destinations: list[NormalizedDestinationV1] | None = None,
        confidence: float = 1.0,
    ) -> NormalizedActionV1:
        normalized_resources = (
            resources if resources is not None else _path_resources(arguments, operation)
        )
        sensitive = any(item.sensitivity == "sensitive" for item in normalized_resources)
        if sensitive:
            flags = [*flags, "sensitive_path_access"]
        return NormalizedActionV1(
            trace_id=trace.trace_id,
            tool_name=trace.proposed_tool_call.tool_name,
            capabilities=capabilities,
            operation=operation,
            resources=normalized_resources,
            destinations=destinations or [],
            side_effect=side_effect,
            reversible=reversible,
            impact=impact,
            flags=sorted(set(flags)),
            parser=ParserResultV1(
                name=self.name,
                version=self.version,
                status="parsed" if confidence == 1.0 else "partial",
                confidence=confidence,
                unsupported_syntax=False,
                detail=f"Classified shell command as {operation}: {raw_command}",
            ),
            argument_hash=trace.proposed_tool_call.argument_hash,
        )

    def _fallback(
        self,
        trace: AgentGuardTraceV1,
        *,
        status: str,
        detail: str,
        flags: list[str],
    ) -> NormalizedActionV1:
        return NormalizedActionV1(
            trace_id=trace.trace_id,
            tool_name=trace.proposed_tool_call.tool_name,
            capabilities=["unknown"],
            operation="unknown",
            side_effect=True,
            reversible=None,
            impact="unknown",
            flags=sorted(set(flags)),
            parser=ParserResultV1(
                name=self.name,
                version=self.version,
                status=status,
                confidence=0.2 if status == "unsupported" else 0.0,
                unsupported_syntax=status == "unsupported",
                detail=detail,
            ),
            argument_hash=trace.proposed_tool_call.argument_hash,
        )


def _path_resources(values: list[str], access: str) -> list[NormalizedResourceV1]:
    resources = []
    for value in values:
        if value.startswith("-") or value in {".", ".."}:
            continue
        if "://" in value:
            continue
        normalized = os.path.expanduser(value)
        sensitivity = (
            "sensitive"
            if any(_path_is_under(normalized, prefix) for prefix in SENSITIVE_PREFIXES)
            else "normal"
        )
        resources.append(
            NormalizedResourceV1(
                type="filesystem_path",
                value=normalized,
                access=access,
                sensitivity=sensitivity,
            )
        )
    return resources


def _path_is_under(value: str, configured_prefix: str) -> bool:
    prefix = os.path.expanduser(configured_prefix)
    normalized_value = os.path.normpath(value)
    normalized_prefix = os.path.normpath(prefix)
    return normalized_value == normalized_prefix or normalized_value.startswith(
        normalized_prefix + os.sep
    )


def _network_destinations(arguments: list[str]) -> list[NormalizedDestinationV1]:
    destinations = []
    for value in arguments:
        if value.startswith("-"):
            continue
        parsed = urlparse(value if "://" in value else f"//{value}")
        host = parsed.hostname
        if host:
            destinations.append(
                NormalizedDestinationV1(
                    type="url" if "://" in value else "host",
                    value=value,
                    external=True,
                )
            )
    return destinations


def _redirection_targets(tokens: list[str]) -> list[str]:
    targets = []
    for index, token in enumerate(tokens[:-1]):
        if token in {">", ">>"}:
            targets.append(tokens[index + 1])
    if targets:
        return targets
    match = re.search(r"(?:>>|>)\s*([^\s]+)", " ".join(tokens))
    return [match.group(1)] if match else []


def _is_package_install(command: str, arguments: list[str]) -> bool:
    if command in {"pip", "pip3", "npm", "pnpm", "yarn", "gem", "brew", "uv"}:
        return "install" in arguments or "add" in arguments
    return "install" in arguments
