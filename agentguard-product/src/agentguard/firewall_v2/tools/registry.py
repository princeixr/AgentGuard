"""Security descriptor generation for built-in and discovered runtime tools."""

from __future__ import annotations

from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.runtime.tool_registry import ToolMetadata

GMAIL_SEND_TOOL_NAMES = {"gmail_send", "gmail_send_email", "gmail_send_draft"}


def descriptor_for_tool(
    tool_name: str,
    metadata: ToolMetadata | None = None,
) -> ToolDescriptorV1:
    if tool_name == "run_shell_command":
        return ToolDescriptorV1(
            tool_name=tool_name,
            provider="local",
            category="shell",
            domain="system",
            operation="dynamic",
            capabilities=["dynamic.shell"],
            side_effect="dynamic_shell_command",
            impact="dynamic",
            reversible=None,
            normalizer="shell_v1",
            external_impact=None,
            privilege_level="user",
            metadata_confidence=1.0,
            metadata_provenance=["built_in"],
            default_tiers=["tier_1"],
            metadata_status="built_in",
            description="Run a local non-interactive shell command.",
        )
    if metadata is not None:
        return _metadata_descriptor(metadata)
    if tool_name.startswith("gmail_"):
        return _gmail_descriptor(tool_name)
    return ToolDescriptorV1(
        tool_name=tool_name,
        provider="unknown",
        category="unknown",
        domain="unknown",
        operation="unknown",
        capabilities=["unknown"],
        side_effect="unknown",
        impact="unknown",
        reversible=None,
        normalizer="unsupported",
        metadata_confidence=0.0,
        metadata_provenance=["fallback"],
        default_tiers=["tier_1"],
        metadata_status="unsupported",
        description="Unsupported tool. AgentGuard will treat this conservatively.",
    )


def descriptors_for_tools(tool_names: list[str]) -> list[ToolDescriptorV1]:
    return [descriptor_for_tool(name) for name in tool_names]


def _gmail_descriptor(tool_name: str) -> ToolDescriptorV1:
    raw_name = tool_name.removeprefix("gmail_")
    if raw_name in {"search", "search_emails"}:
        capability = "email.search"
        side_effect = None
        impact = "low"
        reversible = True
    elif raw_name in {"read", "read_email"}:
        capability = "email.read"
        side_effect = None
        impact = "low"
        reversible = True
    elif raw_name in {"draft", "draft_email"}:
        capability = "email.draft"
        side_effect = "local_draft_create"
        impact = "medium"
        reversible = True
    elif raw_name in {"send", "send_email", "send_draft"}:
        capability = "email.send"
        side_effect = "external_message_send"
        impact = "high"
        reversible = False
    else:
        capability = "email.unknown"
        side_effect = "unknown"
        impact = "unknown"
        reversible = None

    return ToolDescriptorV1(
        tool_name=tool_name,
        provider="gmail_mcp",
        category="email",
        domain="communication",
        operation=raw_name.split("_", 1)[0],
        capabilities=[capability],
        side_effect=side_effect,
        impact=impact,
        reversible=reversible,
        normalizer="gmail_v1",
        external_impact=capability == "email.send",
        metadata_confidence=0.8,
        metadata_provenance=["legacy_builtin"],
        default_tiers=["tier_1"],
        metadata_status="built_in",
        description=f"Gmail MCP tool {raw_name}.",
    )


def _metadata_descriptor(metadata: ToolMetadata) -> ToolDescriptorV1:
    capabilities = list(metadata.capabilities)
    supported = (
        metadata.operation != "unknown"
        and bool(capabilities)
        and metadata.metadata_confidence > 0
    )
    side_effect = metadata.side_effect_type
    if side_effect is None and metadata.risk_level.value != "read_only":
        side_effect = f"{metadata.category}_{metadata.operation}"
    impact = {
        "read_only": "low",
        "low_side_effect": "medium",
        "external_write": "high",
        "irreversible": "high",
        "high_risk": "high",
    }.get(metadata.risk_level.value, "unknown")
    domain = {
        "email": "communication",
        "file": "workspace",
        "calendar": "scheduling",
        "web": "network",
    }.get(metadata.category, metadata.category)
    return ToolDescriptorV1(
        tool_name=metadata.name,
        provider=metadata.provider or "runtime",
        category=metadata.category,
        domain=domain,
        operation=metadata.operation,
        capabilities=capabilities or ["unknown"],
        side_effect=side_effect,
        impact=impact,
        reversible=not metadata.irreversible,
        normalizer="structured_v1" if supported else "unsupported",
        input_schema=metadata.input_schema,
        argument_roles={
            role: list(fields)
            for role, fields in metadata.argument_roles.items()
        },
        required_arguments=list(metadata.required_arguments),
        external_impact=metadata.external_impact,
        privilege_level=metadata.privilege_level,
        declared_data_classes=list(metadata.data_classes),
        metadata_confidence=metadata.metadata_confidence,
        metadata_provenance=list(metadata.metadata_provenance),
        default_tiers=["tier_1"],
        metadata_status="inferred" if supported else "unsupported",
        description=metadata.description,
    )
