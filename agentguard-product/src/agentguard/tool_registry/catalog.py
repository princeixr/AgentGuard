"""Built-in metadata for common agent tools.

The registry gives open-source users a low-friction path: pass a tool name or a
compact type such as ``email.send`` and AgentGuard fills the richer governance
metadata needed by the firewall.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentguard.server.models import ToolManifest


@dataclass(frozen=True)
class BuiltInToolMetadata:
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
    argument_roles: dict[str, tuple[str, ...]] = field(default_factory=dict)
    aliases: tuple[str, ...] = ()

    def agentguard_annotations(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool_type": self.tool_type,
            "domain": self.domain,
            "operation": self.operation,
            "capabilities": list(self.capabilities),
            "risk_level": self.risk_level,
            "side_effect_type": self.side_effect_type,
            "reversible": self.reversible,
            "requires_approval_default": self.requires_approval_default,
            "argument_roles": {
                key: list(value) for key, value in self.argument_roles.items()
            },
        }
        if overrides:
            payload.update(overrides)
        return payload


BUILT_IN_TOOLS: dict[str, BuiltInToolMetadata] = {
    "email.send": BuiltInToolMetadata(
        tool_type="email.send",
        display_name="Send Email",
        domain="email",
        operation="send",
        capabilities=("email.send",),
        risk_level="high_risk",
        provider="email",
        side_effect_type="external_write",
        reversible=False,
        requires_approval_default=True,
        argument_roles={
            "recipient": ("to", "recipient", "email"),
            "subject": ("subject",),
            "body": ("body", "message", "content"),
        },
        aliases=("send_email", "send_gmail", "gmail_send", "email_user"),
    ),
    "email.draft": BuiltInToolMetadata(
        tool_type="email.draft",
        display_name="Draft Email",
        domain="email",
        operation="draft",
        capabilities=("email.draft",),
        risk_level="medium_risk",
        provider="email",
        side_effect_type="local_write",
        reversible=True,
        argument_roles={"recipient": ("to", "recipient", "email")},
        aliases=("draft_email", "create_email_draft", "gmail_draft"),
    ),
    "file.read": BuiltInToolMetadata(
        tool_type="file.read",
        display_name="Read File",
        domain="filesystem",
        operation="read",
        capabilities=("file.read",),
        risk_level="medium_risk",
        provider="filesystem",
        aliases=("read_file", "load_file", "open_file"),
    ),
    "file.write": BuiltInToolMetadata(
        tool_type="file.write",
        display_name="Write File",
        domain="filesystem",
        operation="write",
        capabilities=("file.write",),
        risk_level="high_risk",
        provider="filesystem",
        side_effect_type="local_write",
        reversible=True,
        requires_approval_default=True,
        aliases=("write_file", "save_file", "edit_file"),
    ),
    "file.delete": BuiltInToolMetadata(
        tool_type="file.delete",
        display_name="Delete File",
        domain="filesystem",
        operation="delete",
        capabilities=("file.delete",),
        risk_level="critical_risk",
        provider="filesystem",
        side_effect_type="destructive_write",
        reversible=False,
        requires_approval_default=True,
        aliases=("delete_file", "remove_file", "rm_file"),
    ),
    "web.search": BuiltInToolMetadata(
        tool_type="web.search",
        display_name="Web Search",
        domain="web",
        operation="search",
        capabilities=("web.search",),
        risk_level="low_risk",
        provider="web",
        aliases=("web_search", "search_web", "google_search"),
    ),
    "calendar.create": BuiltInToolMetadata(
        tool_type="calendar.create",
        display_name="Create Calendar Event",
        domain="calendar",
        operation="create",
        capabilities=("calendar.create",),
        risk_level="medium_risk",
        provider="calendar",
        side_effect_type="external_write",
        reversible=True,
        requires_approval_default=True,
        aliases=("create_calendar_event", "calendar_create_event", "schedule_meeting"),
    ),
    "payment.send": BuiltInToolMetadata(
        tool_type="payment.send",
        display_name="Send Payment",
        domain="payments",
        operation="send",
        capabilities=("payment.send",),
        risk_level="critical_risk",
        provider="payments",
        side_effect_type="financial_write",
        reversible=False,
        requires_approval_default=True,
        argument_roles={"amount": ("amount", "total"), "recipient": ("to", "recipient")},
        aliases=("send_payment", "pay_user", "transfer_money"),
    ),
    "shell.command": BuiltInToolMetadata(
        tool_type="shell.command",
        display_name="Run Shell Command",
        domain="system",
        operation="execute",
        capabilities=("shell.execute",),
        risk_level="critical_risk",
        provider="shell",
        side_effect_type="system_execute",
        reversible=False,
        requires_approval_default=True,
        aliases=("run_shell", "shell_command", "execute_command"),
    ),
}

_ALIAS_TO_TYPE = {
    alias: metadata.tool_type
    for metadata in BUILT_IN_TOOLS.values()
    for alias in (metadata.tool_type, *metadata.aliases)
}


def infer_tool_metadata(
    *,
    name: str,
    tool_type: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> BuiltInToolMetadata:
    resolved_type = tool_type or _ALIAS_TO_TYPE.get(_normalize(name))
    if resolved_type and resolved_type in BUILT_IN_TOOLS:
        return _apply_overrides(BUILT_IN_TOOLS[resolved_type], overrides)
    inferred_type = _infer_from_name(name)
    if inferred_type in BUILT_IN_TOOLS:
        return _apply_overrides(BUILT_IN_TOOLS[inferred_type], overrides)
    return _apply_overrides(
        BuiltInToolMetadata(
            tool_type=tool_type or f"custom.{_normalize(name)}",
            display_name=name.replace("_", " ").strip().title() or "Custom Tool",
            domain="custom",
            operation="execute",
            capabilities=(tool_type or f"custom.{_normalize(name)}",),
            risk_level="high_risk",
            side_effect_type="unknown",
            requires_approval_default=True,
            aliases=(name,),
        ),
        overrides,
    )


def manifest_from_tool(
    *,
    name: str,
    tool_type: str | None = None,
    description: str | None = None,
    input_schema: dict[str, Any] | None = None,
    framework: str = "custom",
    transport: str = "native",
    provider: str | None = None,
    annotations: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> ToolManifest:
    metadata = infer_tool_metadata(name=name, tool_type=tool_type, overrides=overrides)
    merged_annotations = dict(annotations or {})
    merged_annotations["agentguard"] = {
        **metadata.agentguard_annotations(),
        **((annotations or {}).get("agentguard") or {}),
    }
    return ToolManifest(
        name=name,
        source_name=name,
        provider=provider or metadata.provider,
        framework=framework,
        transport=transport,
        description=description or metadata.display_name,
        input_schema=input_schema or {"type": "object"},
        annotations=merged_annotations,
        metadata_provenance=["agentguard_builtin_registry"],
    )


def _infer_from_name(name: str) -> str | None:
    normalized = _normalize(name)
    if "gmail" in normalized or "email" in normalized:
        if any(token in normalized for token in ("send", "reply", "forward")):
            return "email.send"
        if "draft" in normalized:
            return "email.draft"
    if "search" in normalized:
        return "web.search"
    if "calendar" in normalized or "meeting" in normalized:
        return "calendar.create"
    if "payment" in normalized or "pay" in normalized or "transfer" in normalized:
        return "payment.send"
    if "shell" in normalized or "command" in normalized:
        return "shell.command"
    if "file" in normalized:
        if "delete" in normalized or "remove" in normalized:
            return "file.delete"
        if "write" in normalized or "save" in normalized or "edit" in normalized:
            return "file.write"
        if "read" in normalized or "open" in normalized:
            return "file.read"
    return None


def _apply_overrides(
    metadata: BuiltInToolMetadata,
    overrides: dict[str, Any] | None,
) -> BuiltInToolMetadata:
    if not overrides:
        return metadata
    values = {
        "tool_type": metadata.tool_type,
        "display_name": metadata.display_name,
        "domain": metadata.domain,
        "operation": metadata.operation,
        "capabilities": metadata.capabilities,
        "risk_level": metadata.risk_level,
        "provider": metadata.provider,
        "side_effect_type": metadata.side_effect_type,
        "reversible": metadata.reversible,
        "requires_approval_default": metadata.requires_approval_default,
        "argument_roles": metadata.argument_roles,
        "aliases": metadata.aliases,
    }
    values.update(overrides)
    if isinstance(values["capabilities"], list):
        values["capabilities"] = tuple(values["capabilities"])
    values["argument_roles"] = {
        key: tuple(value) for key, value in values["argument_roles"].items()
    }
    if isinstance(values["aliases"], list):
        values["aliases"] = tuple(values["aliases"])
    return BuiltInToolMetadata(**values)


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(".", "_")
