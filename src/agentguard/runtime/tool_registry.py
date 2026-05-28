"""Registry for runtime tools and metadata."""

from dataclasses import dataclass
from typing import Callable

from agentguard.core.enums import ToolRiskLevel


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    category: str
    risk_level: ToolRiskLevel


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._metadata: dict[str, ToolMetadata] = {}

    def register(
        self,
        tool_name: str,
        fn: Callable,
        category: str,
        risk_level: ToolRiskLevel,
    ) -> None:
        self._tools[tool_name] = fn
        self._metadata[tool_name] = ToolMetadata(tool_name, category, risk_level)

    def get(self, tool_name: str) -> Callable:
        return self._tools[tool_name]

    def metadata(self, tool_name: str) -> ToolMetadata:
        return self._metadata[tool_name]

    def names(self) -> list[str]:
        return sorted(self._tools)

