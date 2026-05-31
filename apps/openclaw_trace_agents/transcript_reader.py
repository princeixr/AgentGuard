"""OpenClaw transcript reader.

Observed OpenClaw CLI session logs are JSONL files under:

`~/.openclaw/agents/<agent>/sessions/<session_id>.jsonl`

The entries are message records. Assistant messages can contain `toolCall` content
items, and following `toolResult` messages contain the outputs.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from apps.openclaw_trace_agents.base import OpenClawToolEvent


class OpenClawTranscriptModelError(Exception):
    """Raised when an OpenClaw transcript contains a model/runtime error."""


class OpenClawTranscriptReader:
    def read_tool_events(self, transcript_path: Path) -> list[OpenClawToolEvent]:
        records = _load_jsonl(transcript_path)
        results_by_call_id = _index_tool_results(records)
        events: list[OpenClawToolEvent] = []

        for record_index, record in enumerate(records, start=1):
            message = record.get("message", {})
            if message.get("role") != "assistant":
                continue
            for content in message.get("content", []):
                if content.get("type") != "toolCall":
                    continue
                call_id = content.get("id")
                result = results_by_call_id.get(call_id, {})
                output_summary = _summarize_tool_result(result)
                tool_name = str(content.get("name", "unknown_tool"))
                arguments = dict(content.get("arguments") or {})
                semantic_tool = _extract_productivity_tool_call(tool_name, arguments)
                if semantic_tool:
                    tool_name, arguments = semantic_tool
                events.append(
                    OpenClawToolEvent(
                        tool_name=tool_name,
                        arguments=arguments,
                        output_summary=output_summary,
                        source_event_id=record.get("id"),
                        source_tool_call_id=call_id,
                        source_record_index=record_index,
                        contains_untrusted_instruction=_contains_untrusted_instruction(output_summary),
                        contains_external_link=_contains_external_link(output_summary),
                        contains_secret_like_content=_contains_secret_like_content(output_summary),
                    )
                )
        return events

    def read_model_errors(self, transcript_path: Path) -> list[str]:
        records = _load_jsonl(transcript_path)
        errors = []
        for record in records:
            message = record.get("message", {})
            if message.get("role") != "assistant":
                continue
            if message.get("stopReason") != "error":
                continue
            provider = message.get("provider") or "unknown_provider"
            model = message.get("model") or "unknown_model"
            error_message = _compact_error_message(message.get("errorMessage"))
            errors.append(f"{provider}/{model}: {error_message}")
        return errors


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _index_tool_results(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results = {}
    for record in records:
        message = record.get("message", {})
        if message.get("role") != "toolResult":
            continue
        tool_call_id = message.get("toolCallId")
        if tool_call_id:
            results[tool_call_id] = message
    return results


def _summarize_tool_result(message: dict[str, Any]) -> str | None:
    if not message:
        return None
    details = message.get("details") or {}
    if details.get("aggregated"):
        return str(details["aggregated"])[:1000]
    chunks = []
    for content in message.get("content", []):
        text = content.get("text")
        if text:
            chunks.append(str(text))
    if not chunks:
        return None
    return "\n".join(chunks)[:1000]


def _compact_error_message(error_message: Any) -> str:
    if not error_message:
        return "unknown error"
    text = str(error_message)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text[:1000]

    nested_message = parsed.get("error", {}).get("message")
    if not nested_message:
        return text[:1000]
    try:
        nested = json.loads(nested_message)
    except json.JSONDecodeError:
        return str(nested_message)[:1000]
    return str(nested.get("error", {}).get("message", nested_message))[:1000]


def _extract_productivity_tool_call(
    native_tool_name: str,
    native_arguments: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    if native_tool_name != "exec":
        return None
    command = native_arguments.get("command")
    if not isinstance(command, str):
        return None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None

    tool_script_index = None
    for index, token in enumerate(tokens):
        if token.endswith("productivity_tool.py"):
            tool_script_index = index
            break
    if tool_script_index is None or tool_script_index + 1 >= len(tokens):
        return None

    semantic_tool_name = tokens[tool_script_index + 1]
    if semantic_tool_name not in _PRODUCTIVITY_TOOL_NAMES:
        return None

    semantic_arguments = _parse_cli_flags(tokens[tool_script_index + 2 :])
    semantic_arguments["_openclaw_native_tool"] = native_tool_name
    semantic_arguments["_openclaw_command"] = command
    return semantic_tool_name, semantic_arguments


def _parse_cli_flags(tokens: list[str]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            index += 1
            continue
        key = token.removeprefix("--").replace("-", "_")
        next_index = index + 1
        if next_index >= len(tokens) or tokens[next_index].startswith("--"):
            arguments[key] = True
            index += 1
            continue
        arguments[key] = tokens[next_index]
        index += 2
    return arguments


def _contains_untrusted_instruction(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return "ignore previous instructions" in lowered or "disregard instructions" in lowered


def _contains_external_link(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return "http://" in lowered or "https://" in lowered


def _contains_secret_like_content(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    markers = ["api_key", "secret", "password", "token"]
    return any(marker in lowered for marker in markers)


_PRODUCTIVITY_TOOL_NAMES = {
    "gmail_search",
    "gmail_read",
    "gmail_draft",
    "gmail_send",
    "file_search",
    "file_read",
    "file_write",
    "file_delete",
    "calendar_search",
    "calendar_read",
    "calendar_create_event",
}
