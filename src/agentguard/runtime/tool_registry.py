"""Registry for runtime tools and metadata."""

from dataclasses import dataclass
from typing import Callable

from agentguard.core.enums import ToolRiskLevel

GMAIL_SEND_TOOL_NAMES = {"gmail_send", "gmail_send_email", "gmail_send_draft"}
GMAIL_DRAFT_TOOL_NAMES = {"gmail_draft", "gmail_draft_email"}


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    category: str
    risk_level: ToolRiskLevel
    side_effect_type: str | None = None
    requires_confirmation_by_default: bool = False
    irreversible: bool = False
    mcp_server: str | None = None
    provider: str | None = None
    description: str | None = None
    action_tags: tuple[str, ...] = ()


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
        side_effect_type: str | None = None,
        requires_confirmation_by_default: bool = False,
        irreversible: bool = False,
        mcp_server: str | None = None,
        provider: str | None = None,
        description: str | None = None,
        action_tags: tuple[str, ...] = (),
    ) -> None:
        self._tools[tool_name] = fn
        self._metadata[tool_name] = ToolMetadata(
            name=tool_name,
            category=category,
            risk_level=risk_level,
            side_effect_type=side_effect_type,
            requires_confirmation_by_default=requires_confirmation_by_default,
            irreversible=irreversible,
            mcp_server=mcp_server,
            provider=provider,
            description=description,
            action_tags=action_tags,
        )

    def register_metadata(self, metadata: ToolMetadata, fn: Callable | None = None) -> None:
        self._metadata[metadata.name] = metadata
        if fn is not None:
            self._tools[metadata.name] = fn

    def get(self, tool_name: str) -> Callable:
        return self._tools[tool_name]

    def metadata(self, tool_name: str) -> ToolMetadata:
        return self._metadata.get(tool_name, infer_tool_metadata(tool_name))

    def names(self) -> list[str]:
        return sorted(set(self._tools) | set(self._metadata))


def infer_tool_metadata(tool_name: str) -> ToolMetadata:
    if tool_name == "run_shell_command":
        category = "terminal"
    elif tool_name.startswith("gmail_"):
        category = "email"
    elif tool_name.startswith("file_"):
        category = "file"
    elif tool_name.startswith("calendar_"):
        category = "calendar"
    else:
        category = "unknown"

    if tool_name == "run_shell_command":
        risk_level = ToolRiskLevel.HIGH_RISK
    elif tool_name in GMAIL_SEND_TOOL_NAMES | {"calendar_create_event", "calendar_update_event"}:
        risk_level = ToolRiskLevel.EXTERNAL_WRITE
    elif tool_name in {"file_delete", "calendar_delete_event"}:
        risk_level = ToolRiskLevel.IRREVERSIBLE
    elif tool_name.endswith("_read") or tool_name.endswith("_search"):
        risk_level = ToolRiskLevel.READ_ONLY
    else:
        risk_level = ToolRiskLevel.LOW_SIDE_EFFECT

    side_effect_type = None
    if tool_name == "run_shell_command":
        side_effect_type = "shell_command"
    elif tool_name in GMAIL_SEND_TOOL_NAMES:
        side_effect_type = "external_message_send"
    elif tool_name in GMAIL_DRAFT_TOOL_NAMES:
        side_effect_type = "local_draft_create"
    elif tool_name == "calendar_create_event":
        side_effect_type = "calendar_event_create"
    elif tool_name == "calendar_update_event":
        side_effect_type = "calendar_event_update"
    elif tool_name == "file_write":
        side_effect_type = "file_write"
    elif tool_name == "file_delete":
        side_effect_type = "file_delete"

    return ToolMetadata(
        name=tool_name,
        category=category,
        risk_level=risk_level,
        side_effect_type=side_effect_type,
        requires_confirmation_by_default=risk_level
        in {ToolRiskLevel.EXTERNAL_WRITE, ToolRiskLevel.IRREVERSIBLE, ToolRiskLevel.HIGH_RISK},
        irreversible=risk_level == ToolRiskLevel.IRREVERSIBLE or tool_name in GMAIL_SEND_TOOL_NAMES,
    )


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for name in [
        "run_shell_command",
        "gmail_search",
        "gmail_read",
        "gmail_draft",
        "gmail_send",
        "gmail_search_emails",
        "gmail_read_email",
        "gmail_draft_email",
        "gmail_send_email",
        "gmail_send_draft",
        "file_search",
        "file_read",
        "file_write",
        "file_delete",
        "calendar_search",
        "calendar_read",
        "calendar_create_event",
        "calendar_update_event",
    ]:
        registry.register_metadata(infer_tool_metadata(name))
    return registry
