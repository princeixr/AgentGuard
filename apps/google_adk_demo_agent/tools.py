"""Tool registration helpers for the Google ADK demo agent."""

from agentguard.core.enums import ToolRiskLevel
from agentguard.runtime.mock_tools.email_tools import gmail_draft, gmail_read, gmail_search, gmail_send
from agentguard.runtime.tool_registry import ToolRegistry


def build_demo_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("gmail_search", gmail_search, "email", ToolRiskLevel.READ_ONLY)
    registry.register("gmail_read", gmail_read, "email", ToolRiskLevel.READ_ONLY)
    registry.register("gmail_draft", gmail_draft, "email", ToolRiskLevel.LOW_SIDE_EFFECT)
    registry.register("gmail_send", gmail_send, "email", ToolRiskLevel.EXTERNAL_WRITE)
    return registry

