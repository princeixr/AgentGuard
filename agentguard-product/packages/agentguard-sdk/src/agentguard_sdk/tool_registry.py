"""Small SDK-side tool registry for easy metadata generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentguard_sdk.models import ToolManifest


@dataclass(frozen=True)
class ToolMetadata:
    tool_type: str
    display_name: str
    domain: str
    operation: str
    capabilities: tuple[str, ...]
    risk_level: str
    provider: str = "custom"
    side_effect_type: str = "none"
    reversible: bool | None = None
    requires_approval_default: bool = False


BUILT_INS = {
    "email.send": ToolMetadata(
        "email.send",
        "Send Email",
        "email",
        "send",
        ("email.send",),
        "high_risk",
        "email",
        "external_write",
        False,
        True,
    ),
    "email.draft": ToolMetadata(
        "email.draft",
        "Draft Email",
        "email",
        "draft",
        ("email.draft",),
        "medium_risk",
        "email",
        "local_write",
        True,
        False,
    ),
    "web.search": ToolMetadata(
        "web.search",
        "Web Search",
        "web",
        "search",
        ("web.search",),
        "low_risk",
        "web",
    ),
    "file.read": ToolMetadata(
        "file.read",
        "Read File",
        "filesystem",
        "read",
        ("file.read",),
        "medium_risk",
        "filesystem",
    ),
    "file.write": ToolMetadata(
        "file.write",
        "Write File",
        "filesystem",
        "write",
        ("file.write",),
        "high_risk",
        "filesystem",
        "local_write",
        True,
        True,
    ),
    "file.delete": ToolMetadata(
        "file.delete",
        "Delete File",
        "filesystem",
        "delete",
        ("file.delete",),
        "critical_risk",
        "filesystem",
        "destructive_write",
        False,
        True,
    ),
    "payment.send": ToolMetadata(
        "payment.send",
        "Send Payment",
        "payments",
        "send",
        ("payment.send",),
        "critical_risk",
        "payments",
        "financial_write",
        False,
        True,
    ),
    "shell.command": ToolMetadata(
        "shell.command",
        "Run Shell Command",
        "system",
        "execute",
        ("shell.execute",),
        "critical_risk",
        "shell",
        "system_execute",
        False,
        True,
    ),
}

ALIASES = {
    "send_email": "email.send",
    "send_gmail": "email.send",
    "draft_email": "email.draft",
    "web_search": "web.search",
    "read_file": "file.read",
    "write_file": "file.write",
    "delete_file": "file.delete",
    "send_payment": "payment.send",
    "shell_command": "shell.command",
}


def manifest_from_tool(
    name: str,
    *,
    tool_type: str | None = None,
    description: str | None = None,
    input_schema: dict[str, Any] | None = None,
    framework: str = "custom",
    transport: str = "native",
    metadata_overrides: dict[str, Any] | None = None,
) -> ToolManifest:
    metadata = infer_tool_metadata(name, tool_type)
    agentguard = {
        "tool_type": metadata.tool_type,
        "domain": metadata.domain,
        "operation": metadata.operation,
        "capabilities": list(metadata.capabilities),
        "risk_level": metadata.risk_level,
        "side_effect_type": metadata.side_effect_type,
        "reversible": metadata.reversible,
        "requires_approval_default": metadata.requires_approval_default,
    }
    if metadata_overrides:
        agentguard.update(metadata_overrides)
    return ToolManifest(
        name=name,
        source_name=name,
        provider=metadata.provider,
        framework=framework,
        transport=transport,
        description=description or metadata.display_name,
        input_schema=input_schema or {"type": "object"},
        annotations={"agentguard": agentguard},
        metadata_provenance=["agentguard_sdk_registry"],
    )


def infer_tool_metadata(name: str, tool_type: str | None = None) -> ToolMetadata:
    resolved = tool_type or ALIASES.get(_normalize(name)) or _infer(name)
    if resolved and resolved in BUILT_INS:
        return BUILT_INS[resolved]
    custom_type = tool_type or f"custom.{_normalize(name)}"
    return ToolMetadata(
        custom_type,
        name.replace("_", " ").title(),
        "custom",
        "execute",
        (custom_type,),
        "high_risk",
        "custom",
        "unknown",
        None,
        True,
    )


def _infer(name: str) -> str | None:
    normalized = _normalize(name)
    if "gmail" in normalized or "email" in normalized:
        return "email.draft" if "draft" in normalized else "email.send"
    if "search" in normalized:
        return "web.search"
    if "payment" in normalized or "pay" in normalized:
        return "payment.send"
    if "shell" in normalized or "command" in normalized:
        return "shell.command"
    if "file" in normalized:
        if "delete" in normalized or "remove" in normalized:
            return "file.delete"
        if "write" in normalized or "save" in normalized or "edit" in normalized:
            return "file.write"
        return "file.read"
    return None


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(".", "_")
