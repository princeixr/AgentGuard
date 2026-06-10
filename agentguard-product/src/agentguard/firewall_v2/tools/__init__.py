"""Tool descriptor and capability registry."""

from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.registry import descriptor_for_tool, descriptors_for_tools

__all__ = ["ToolDescriptorV1", "descriptor_for_tool", "descriptors_for_tools"]
