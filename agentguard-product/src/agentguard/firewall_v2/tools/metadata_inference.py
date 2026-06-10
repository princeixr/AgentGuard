"""Infer guard-side security metadata from sanitized tool manifests."""

from __future__ import annotations

import re
from typing import Any

from agentguard.control_plane.models import RegisteredTool
from agentguard.core.enums import ToolRiskLevel
from agentguard.runtime.tool_registry import ToolMetadata

_OPERATIONS = {
    "delete": ("delete", ToolRiskLevel.IRREVERSIBLE),
    "remove": ("delete", ToolRiskLevel.IRREVERSIBLE),
    "send": ("send", ToolRiskLevel.EXTERNAL_WRITE),
    "transfer": ("transfer", ToolRiskLevel.HIGH_RISK),
    "pay": ("execute", ToolRiskLevel.HIGH_RISK),
    "create": ("create", ToolRiskLevel.LOW_SIDE_EFFECT),
    "write": ("write", ToolRiskLevel.LOW_SIDE_EFFECT),
    "update": ("update", ToolRiskLevel.LOW_SIDE_EFFECT),
    "modify": ("update", ToolRiskLevel.LOW_SIDE_EFFECT),
    "draft": ("draft", ToolRiskLevel.LOW_SIDE_EFFECT),
    "search": ("search", ToolRiskLevel.READ_ONLY),
    "list": ("list", ToolRiskLevel.READ_ONLY),
    "read": ("read", ToolRiskLevel.READ_ONLY),
    "get": ("read", ToolRiskLevel.READ_ONLY),
}
_DOMAINS = {
    "gmail": "email",
    "email": "email",
    "mail": "email",
    "calendar": "calendar",
    "event": "calendar",
    "drive": "drive",
    "file": "file",
    "filesystem": "file",
    "web": "web",
    "search": "web",
    "payment": "payment",
    "wallet": "payment",
    "shell": "terminal",
    "terminal": "terminal",
}
_ARGUMENT_ROLES = {
    "to": "destination",
    "cc": "destination",
    "bcc": "destination",
    "recipient": "destination",
    "recipients": "destination",
    "email": "destination",
    "url": "destination",
    "domain": "destination",
    "path": "resource",
    "file": "resource",
    "file_path": "resource",
    "folder": "resource",
    "folder_id": "resource",
    "event_id": "resource",
    "message_id": "resource",
    "amount": "estimated_value",
    "value": "estimated_value",
    "body": "content",
    "content": "content",
    "message": "content",
    "query": "query",
}


def infer_registered_tool_metadata(tool: RegisteredTool) -> ToolMetadata:
    """Build conservative metadata without using agent connection secrets."""
    explicit = tool.annotations.get("agentguard", {})
    if isinstance(explicit, dict) and explicit.get("capabilities"):
        return _from_explicit_annotations(tool, explicit)

    tokens = _tokens(tool)
    operation, risk = _infer_operation(tokens)
    category = _infer_domain(tokens)
    roles = _infer_argument_roles(tool.input_schema)
    capabilities = ()
    if category != "unknown" and operation != "unknown":
        capability_domain = {
            "email": "email",
            "calendar": "calendar",
            "drive": "drive",
            "file": "filesystem",
            "web": "web",
            "payment": "payment",
            "terminal": "dynamic",
        }.get(category, category)
        capability_operation = "shell" if category == "terminal" else operation
        capabilities = (f"{capability_domain}.{capability_operation}",)

    confidence = 0.85 if capabilities else 0.25
    return ToolMetadata(
        name=tool.name,
        category=category,
        risk_level=risk,
        side_effect_type=None if risk == ToolRiskLevel.READ_ONLY else f"{category}_{operation}",
        requires_confirmation_by_default=risk
        in {
            ToolRiskLevel.EXTERNAL_WRITE,
            ToolRiskLevel.IRREVERSIBLE,
            ToolRiskLevel.HIGH_RISK,
        },
        irreversible=risk == ToolRiskLevel.IRREVERSIBLE,
        provider=tool.provider,
        description=tool.description,
        operation=operation,
        capabilities=capabilities,
        input_schema=tool.input_schema,
        argument_roles=roles,
        required_arguments=tuple(tool.input_schema.get("required", [])),
        external_impact=risk in {ToolRiskLevel.EXTERNAL_WRITE, ToolRiskLevel.HIGH_RISK},
        metadata_confidence=confidence,
        metadata_provenance=(*tool.metadata_provenance, "guard_manifest_inference_v1"),
    )


def _from_explicit_annotations(
    tool: RegisteredTool,
    values: dict[str, Any],
) -> ToolMetadata:
    risk_value = str(values.get("risk_level", "high_risk"))
    try:
        risk = ToolRiskLevel(risk_value)
    except ValueError:
        risk = ToolRiskLevel.HIGH_RISK
    return ToolMetadata(
        name=tool.name,
        category=str(values.get("domain", "unknown")),
        risk_level=risk,
        side_effect_type=values.get("side_effect_type"),
        requires_confirmation_by_default=bool(
            values.get("requires_confirmation", risk != ToolRiskLevel.READ_ONLY)
        ),
        irreversible=bool(values.get("irreversible", False)),
        provider=tool.provider,
        description=tool.description,
        operation=str(values.get("operation", "unknown")),
        capabilities=tuple(str(item) for item in values.get("capabilities", [])),
        input_schema=tool.input_schema,
        argument_roles={
            str(role): tuple(str(field) for field in fields)
            for role, fields in values.get("argument_roles", {}).items()
        },
        required_arguments=tuple(tool.input_schema.get("required", [])),
        external_impact=values.get("external_impact"),
        privilege_level=str(values.get("privilege_level", "standard")),
        data_classes=tuple(str(item) for item in values.get("data_classes", [])),
        metadata_confidence=float(values.get("confidence", 1.0)),
        metadata_provenance=(*tool.metadata_provenance, "agent_declaration"),
    )


def _tokens(tool: RegisteredTool) -> set[str]:
    text = f"{tool.name} {tool.source_name} {tool.provider} {tool.description}".lower()
    return set(re.findall(r"[a-z0-9]+", text))


def _infer_operation(tokens: set[str]) -> tuple[str, ToolRiskLevel]:
    for token, result in _OPERATIONS.items():
        if token in tokens:
            return result
    return "unknown", ToolRiskLevel.HIGH_RISK


def _infer_domain(tokens: set[str]) -> str:
    for token, domain in _DOMAINS.items():
        if token in tokens:
            return domain
    return "unknown"


def _infer_argument_roles(schema: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    roles: dict[str, list[str]] = {}
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return {}
    for field in properties:
        role = _ARGUMENT_ROLES.get(str(field).lower())
        if role:
            roles.setdefault(role, []).append(str(field))
    return {role: tuple(fields) for role, fields in roles.items()}
