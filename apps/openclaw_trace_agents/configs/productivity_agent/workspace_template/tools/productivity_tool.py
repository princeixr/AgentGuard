#!/usr/bin/env python3
"""Deterministic local productivity tools for OpenClaw trace generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "data" / "productivity_seed.json"
STATE_DIR = ROOT / "state"
DRAFTS_PATH = STATE_DIR / "drafts.json"
SENT_PATH = STATE_DIR / "sent.json"
CREATED_EVENTS_PATH = STATE_DIR / "created_events.json"
WRITTEN_FILES_PATH = STATE_DIR / "written_files.json"
DELETED_FILES_PATH = STATE_DIR / "deleted_files.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="tool_name", required=True)

    gmail_search = subparsers.add_parser("gmail_search")
    gmail_search.add_argument("--query", required=True)

    gmail_read = subparsers.add_parser("gmail_read")
    gmail_read.add_argument("--thread-id", required=True)

    gmail_draft = subparsers.add_parser("gmail_draft")
    gmail_draft.add_argument("--thread-id", required=True)
    gmail_draft.add_argument("--body", required=True)

    gmail_send = subparsers.add_parser("gmail_send")
    gmail_send.add_argument("--draft-id", required=True)

    file_search = subparsers.add_parser("file_search")
    file_search.add_argument("--query", required=True)

    file_read = subparsers.add_parser("file_read")
    file_read.add_argument("--path", required=True)

    file_write = subparsers.add_parser("file_write")
    file_write.add_argument("--path", required=True)
    file_write.add_argument("--content", required=True)

    file_delete = subparsers.add_parser("file_delete")
    file_delete.add_argument("--path", required=True)

    calendar_search = subparsers.add_parser("calendar_search")
    calendar_search.add_argument("--query", required=False, default="")

    calendar_read = subparsers.add_parser("calendar_read")
    calendar_read.add_argument("--event-id", required=True)

    calendar_create = subparsers.add_parser("calendar_create_event")
    calendar_create.add_argument("--title", required=True)
    calendar_create.add_argument("--start", required=True)
    calendar_create.add_argument("--end", required=True)
    calendar_create.add_argument("--attendees", required=False, default="")

    args = parser.parse_args()
    seed = _load_seed()
    output = dispatch(args, seed)
    print(json.dumps(output, indent=2, sort_keys=True))


def dispatch(args: argparse.Namespace, seed: dict[str, Any]) -> dict[str, Any]:
    match args.tool_name:
        case "gmail_search":
            return _gmail_search(seed, args.query)
        case "gmail_read":
            return _gmail_read(seed, args.thread_id)
        case "gmail_draft":
            return _gmail_draft(args.thread_id, args.body)
        case "gmail_send":
            return _gmail_send(args.draft_id)
        case "file_search":
            return _file_search(seed, args.query)
        case "file_read":
            return _file_read(seed, args.path)
        case "file_write":
            return _file_write(args.path, args.content)
        case "file_delete":
            return _file_delete(args.path)
        case "calendar_search":
            return _calendar_search(seed, args.query)
        case "calendar_read":
            return _calendar_read(seed, args.event_id)
        case "calendar_create_event":
            attendees = [item.strip() for item in args.attendees.split(",") if item.strip()]
            return _calendar_create_event(args.title, args.start, args.end, attendees)
    raise ValueError(f"Unsupported tool: {args.tool_name}")


def _gmail_search(seed: dict[str, Any], query: str) -> dict[str, Any]:
    query_text = query.lower()
    matches = []
    for thread in seed["email_threads"]:
        searchable = " ".join(
            [
                thread["subject"],
                " ".join(thread["participants"]),
                " ".join(message["body"] for message in thread["messages"]),
            ]
        ).lower()
        if query_text in searchable:
            matches.append(
                {
                    "thread_id": thread["thread_id"],
                    "subject": thread["subject"],
                    "participants": thread["participants"],
                    "received_at": thread["received_at"],
                    "snippet": thread["messages"][-1]["body"][:180],
                }
            )
    return {"tool": "gmail_search", "query": query, "results": matches}


def _gmail_read(seed: dict[str, Any], thread_id: str) -> dict[str, Any]:
    thread = _find_by_key(seed["email_threads"], "thread_id", thread_id)
    return {"tool": "gmail_read", "thread": thread}


def _gmail_draft(thread_id: str, body: str) -> dict[str, Any]:
    drafts = _load_state_list(DRAFTS_PATH)
    draft_id = f"draft_{len(drafts) + 1:03d}"
    draft = {"draft_id": draft_id, "thread_id": thread_id, "body": body, "status": "created"}
    drafts.append(draft)
    _write_state_list(DRAFTS_PATH, drafts)
    return {"tool": "gmail_draft", "draft": draft}


def _gmail_send(draft_id: str) -> dict[str, Any]:
    sent = _load_state_list(SENT_PATH)
    record = {"draft_id": draft_id, "status": "sent"}
    sent.append(record)
    _write_state_list(SENT_PATH, sent)
    return {"tool": "gmail_send", "sent": record}


def _file_search(seed: dict[str, Any], query: str) -> dict[str, Any]:
    query_text = query.lower()
    results = []
    for file_record in seed["files"]:
        searchable = f"{file_record['path']} {file_record['title']} {file_record['content']}".lower()
        if query_text in searchable:
            results.append(
                {
                    "path": file_record["path"],
                    "title": file_record["title"],
                    "snippet": file_record["content"][:180],
                }
            )
    return {"tool": "file_search", "query": query, "results": results}


def _file_read(seed: dict[str, Any], path: str) -> dict[str, Any]:
    file_record = _find_by_key(seed["files"], "path", path)
    return {"tool": "file_read", "file": file_record}


def _file_write(path: str, content: str) -> dict[str, Any]:
    records = _load_state_list(WRITTEN_FILES_PATH)
    record = {"path": path, "content": content, "status": "written"}
    records.append(record)
    _write_state_list(WRITTEN_FILES_PATH, records)
    return {"tool": "file_write", "file": record}


def _file_delete(path: str) -> dict[str, Any]:
    records = _load_state_list(DELETED_FILES_PATH)
    record = {"path": path, "status": "deleted"}
    records.append(record)
    _write_state_list(DELETED_FILES_PATH, records)
    return {"tool": "file_delete", "deleted": record}


def _calendar_search(seed: dict[str, Any], query: str) -> dict[str, Any]:
    query_text = query.lower()
    results = []
    for event in seed["calendar_events"]:
        searchable = f"{event['title']} {event['start']} {event['end']} {event['notes']}".lower()
        if not query_text or query_text in searchable or "tomorrow" in query_text:
            results.append(
                {
                    "event_id": event["event_id"],
                    "title": event["title"],
                    "start": event["start"],
                    "end": event["end"],
                    "attendees": event["attendees"],
                }
            )
    return {"tool": "calendar_search", "query": query, "results": results}


def _calendar_read(seed: dict[str, Any], event_id: str) -> dict[str, Any]:
    event = _find_by_key(seed["calendar_events"], "event_id", event_id)
    return {"tool": "calendar_read", "event": event}


def _calendar_create_event(title: str, start: str, end: str, attendees: list[str]) -> dict[str, Any]:
    records = _load_state_list(CREATED_EVENTS_PATH)
    event_id = f"created_{len(records) + 1:03d}"
    event = {
        "event_id": event_id,
        "title": title,
        "start": start,
        "end": end,
        "attendees": attendees,
        "status": "created",
    }
    records.append(event)
    _write_state_list(CREATED_EVENTS_PATH, records)
    return {"tool": "calendar_create_event", "event": event}


def _load_seed() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _find_by_key(records: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for record in records:
        if record.get(key) == value:
            return record
    return {"error": "not_found", key: value}


def _load_state_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state_list(path: Path, records: list[dict[str, Any]]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
