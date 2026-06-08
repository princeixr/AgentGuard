"""Built-in capability registry for the current demo tools."""

from __future__ import annotations

from agentguard.firewall_v2.tools.models import ToolDescriptorV1

GMAIL_SEND_TOOL_NAMES = {"gmail_send", "gmail_send_email", "gmail_send_draft"}


def descriptor_for_tool(tool_name: str) -> ToolDescriptorV1:
    if tool_name == "run_shell_command":
        return ToolDescriptorV1(
            tool_name=tool_name,
            provider="local",
            category="shell",
            capabilities=["dynamic.shell"],
            side_effect="dynamic_shell_command",
            impact="dynamic",
            reversible=None,
            normalizer="shell_v1",
            default_tiers=["tier_1"],
            metadata_status="built_in",
            description="Run a local non-interactive shell command.",
        )
    if tool_name.startswith("gmail_"):
        return _gmail_descriptor(tool_name)
    return ToolDescriptorV1(
        tool_name=tool_name,
        provider="unknown",
        category="unknown",
        capabilities=["unknown"],
        side_effect="unknown",
        impact="unknown",
        reversible=None,
        normalizer="unsupported",
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
        capabilities=[capability],
        side_effect=side_effect,
        impact=impact,
        reversible=reversible,
        normalizer="gmail_v1",
        default_tiers=["tier_1"],
        metadata_status="built_in",
        description=f"Gmail MCP tool {raw_name}.",
    )

