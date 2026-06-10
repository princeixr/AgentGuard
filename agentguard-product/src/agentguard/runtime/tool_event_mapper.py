"""Mapping helpers from runtime-specific tool events into AgentGuard models."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from agentguard.core.enums import ToolRiskLevel
from agentguard.core.models import ProposedToolCall

GMAIL_SEND_TOOL_NAMES = {"gmail_send", "gmail_send_email", "gmail_send_draft"}
GMAIL_DRAFT_TOOL_NAMES = {"gmail_draft", "gmail_draft_email"}


def infer_tool_category(tool_name: str) -> str:
    if tool_name == "run_shell_command":
        return "terminal"
    if tool_name.startswith("gmail_"):
        return "email"
    if tool_name.startswith("file_"):
        return "file"
    if tool_name.startswith("calendar_"):
        return "calendar"
    return "unknown"


def infer_tool_risk_level(tool_name: str) -> ToolRiskLevel:
    if tool_name == "run_shell_command":
        return ToolRiskLevel.HIGH_RISK
    if tool_name in GMAIL_SEND_TOOL_NAMES | {"calendar_create_event", "calendar_update_event"}:
        return ToolRiskLevel.EXTERNAL_WRITE
    if tool_name in {"file_delete", "calendar_delete_event"}:
        return ToolRiskLevel.IRREVERSIBLE
    if tool_name.endswith("_read") or tool_name.endswith("_search") or tool_name == "file_summarize":
        return ToolRiskLevel.READ_ONLY
    return ToolRiskLevel.LOW_SIDE_EFFECT


def summarize_arguments(arguments: dict[str, Any]) -> str:
    if not arguments:
        return "no arguments"
    return ", ".join(f"{key}={value}" for key, value in sorted(arguments.items()))


def map_event_to_proposed_call(
    event: dict[str, Any],
    session_id: str,
    step_index: int,
    proposed_by: str = "mock_agent",
) -> ProposedToolCall:
    tool_name = str(event["tool_name"])
    arguments = dict(event.get("arguments", {}))
    return ProposedToolCall(
        call_id=str(event.get("call_id") or uuid4()),
        session_id=session_id,
        step_index=step_index,
        tool_name=tool_name,
        tool_category=infer_tool_category(tool_name),
        risk_level=infer_tool_risk_level(tool_name),
        arguments=arguments,
        argument_summary=summarize_arguments(arguments),
        proposed_by=proposed_by,
    )
