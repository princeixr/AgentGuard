"""Serve the OpenClaw productivity environment UI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
for import_path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from _bootstrap import bootstrap
from agentguard.core.models import ScenarioRecord
from agentguard.evaluation.dataset_models import BenchmarkTraceRecord, TraceSourceProvenance
from agentguard.tracing.adapters.openclaw_trace_adapter import OpenClawTraceV1Adapter
from agentguard.tracing.serializers import append_jsonl
from agentguard.tracing.trace_store import TraceStore
from apps.openclaw_trace_agents.cli_runner import OpenClawCliRunner
from apps.openclaw_trace_agents.event_normalizer import OpenClawEventNormalizer
from apps.openclaw_trace_agents.transcript_reader import OpenClawTranscriptReader

UI_ROOT = REPO_ROOT / "apps" / "openclaw_trace_agents" / "productivity_ui"
TEMPLATE_ROOT = (
    REPO_ROOT
    / "apps"
    / "openclaw_trace_agents"
    / "configs"
    / "productivity_agent"
    / "workspace_template"
)
DEFAULT_WORKSPACE = REPO_ROOT / ".openclaw-traces" / "productivity_workspace"
STATE_FILES = {
    "drafts": "drafts.json",
    "sent": "sent.json",
    "created_events": "created_events.json",
    "written_files": "written_files.json",
    "deleted_files": "deleted_files.json",
}
TOOL_FLAGS = {
    "gmail_search": ["query"],
    "gmail_read": ["thread_id"],
    "gmail_draft": ["thread_id", "body"],
    "gmail_send": ["draft_id"],
    "file_search": ["query"],
    "file_read": ["path"],
    "file_write": ["path", "content"],
    "file_delete": ["path"],
    "calendar_search": ["query"],
    "calendar_read": ["event_id"],
    "calendar_create_event": ["title", "start", "end", "attendees"],
}


def main() -> None:
    bootstrap()
    workspace = _workspace_path()
    _ensure_workspace(workspace)
    host = os.environ.get("OPENCLAW_PRODUCTIVITY_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("OPENCLAW_PRODUCTIVITY_UI_PORT", "8765"))
    handler = _build_handler(workspace)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"OpenClaw productivity UI: http://{host}:{port}")
    print(f"Workspace: {workspace}")
    server.serve_forever()


def _build_handler(workspace: Path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(UI_ROOT), **kwargs)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                self._send_json(_environment_state(workspace))
                return
            if parsed.path == "/api/config":
                self._send_json(_config_state(workspace))
                return
            super().do_GET()

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/reset":
                _reset_state(workspace)
                self._send_json(_environment_state(workspace))
                return
            if parsed.path == "/api/tool":
                payload = self._read_json()
                result = _run_productivity_tool(workspace, payload)
                self._send_json({"result": result, "state": _environment_state(workspace)})
                return
            if parsed.path == "/api/agent/run":
                payload = self._read_json()
                result = _run_openclaw_agent(workspace, payload)
                self._send_json({"result": result, "state": _environment_state(workspace)})
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

        def log_message(self, format: str, *args) -> None:
            if self.path.startswith("/api/"):
                return
            super().log_message(format, *args)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def _workspace_path() -> Path:
    value = os.environ.get("OPENCLAW_TRACE_PRODUCTIVITY_WORKSPACE")
    if not value:
        return DEFAULT_WORKSPACE
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def _ensure_workspace(workspace: Path) -> None:
    shutil.copytree(TEMPLATE_ROOT, workspace, dirs_exist_ok=True)
    tool_path = workspace / "tools" / "productivity_tool.py"
    if tool_path.exists():
        tool_path.chmod(0o755)


def _config_state(workspace: Path) -> dict[str, Any]:
    return {
        "profile": os.environ.get("OPENCLAW_TRACE_PROFILE", "agentguard-traces"),
        "agent": os.environ.get("OPENCLAW_TRACE_PRODUCTIVITY_AGENT", "agentguard_productivity"),
        "workspace": str(workspace),
        "trace_root": os.environ.get("AGENTGUARD_RAW_TRACE_ROOT", "data/traces"),
        "raw_root": os.environ.get("OPENCLAW_RAW_ARTIFACT_ROOT", "data/openclaw_raw"),
    }


def _environment_state(workspace: Path) -> dict[str, Any]:
    seed = _load_json(workspace / "data" / "productivity_seed.json", default={})
    state = {
        key: _load_json(workspace / "state" / filename, default=[])
        for key, filename in STATE_FILES.items()
    }
    deleted_paths = {record.get("path") for record in state["deleted_files"]}
    files = [
        {**record, "source": "seed", "deleted": record.get("path") in deleted_paths}
        for record in seed.get("files", [])
    ]
    files.extend({**record, "source": "written", "deleted": False} for record in state["written_files"])
    calendar_events = [
        {**record, "source": "seed"} for record in seed.get("calendar_events", [])
    ]
    calendar_events.extend({**record, "source": "created"} for record in state["created_events"])
    return {
        "workspace": str(workspace),
        "email": {
            "inbox": seed.get("email_threads", []),
            "drafts": state["drafts"],
            "sent": state["sent"],
        },
        "files": files,
        "calendar": {"events": calendar_events},
        "state": state,
        "counts": {
            "inbox": len(seed.get("email_threads", [])),
            "drafts": len(state["drafts"]),
            "sent": len(state["sent"]),
            "files": len(files),
            "calendar": len(calendar_events),
            "writes": len(state["written_files"]),
            "deleted": len(state["deleted_files"]),
        },
    }


def _reset_state(workspace: Path) -> None:
    state_dir = workspace / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    for filename in STATE_FILES.values():
        path = state_dir / filename
        if path.exists():
            path.unlink()


def _run_productivity_tool(workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    tool_name = str(payload.get("tool_name") or "")
    arguments = payload.get("arguments") or {}
    if tool_name not in TOOL_FLAGS:
        raise ValueError(f"Unsupported productivity tool: {tool_name}")
    command = ["python3", "tools/productivity_tool.py", tool_name]
    for key in TOOL_FLAGS[tool_name]:
        value = arguments.get(key)
        if value in (None, "") and key != "query":
            raise ValueError(f"Missing required argument: {key}")
        if value not in (None, ""):
            command.extend([f"--{key.replace('_', '-')}", str(value)])
    completed = subprocess.run(
        command,
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "command": command,
            "stderr": completed.stderr,
            "stdout": completed.stdout,
        }
    return {"ok": True, "command": command, "output": json.loads(completed.stdout)}


def _run_openclaw_agent(workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message") or "").strip()
    if not message:
        raise ValueError("message is required")
    profile = os.environ.get("OPENCLAW_TRACE_PROFILE", "agentguard-traces")
    agent = os.environ.get("OPENCLAW_TRACE_PRODUCTIVITY_AGENT", "agentguard_productivity")
    timeout_seconds = int(payload.get("timeout_seconds") or 180)
    scenario = ScenarioRecord(
        scenario_id="ui_productivity",
        domain="productivity",
        task_category="interactive_environment",
        user_request=message,
        expected_allowed_tools=sorted(TOOL_FLAGS),
        expected_disallowed_tools=[],
        failure_type="none",
        agent_behavior_mode="interactive",
        gold_final_verdict="allow",
    )
    raw_root = REPO_ROOT / os.environ.get("OPENCLAW_RAW_ARTIFACT_ROOT", "data/openclaw_raw")
    trace_root = REPO_ROOT / os.environ.get("AGENTGUARD_RAW_TRACE_ROOT", "data/traces")
    runner = OpenClawCliRunner(
        output_root=raw_root / "runs",
        profile=profile,
        timeout_seconds=timeout_seconds,
    )
    run_result = runner.run(scenario=scenario, agent_name=agent, run_index=1)
    if run_result.transcript_path is None:
        return {
            "ok": False,
            "error": "OpenClaw did not produce a transcript",
            "run": run_result.model_dump(mode="json"),
        }

    reader = OpenClawTranscriptReader()
    errors = reader.read_model_errors(run_result.transcript_path)
    events = reader.read_tool_events(run_result.transcript_path)
    traces = OpenClawEventNormalizer().normalize_events(
        agent_id=f"openclaw_{agent}",
        domain="productivity",
        scenario=scenario,
        events=events,
        session_id=run_result.session_id,
    )
    trace_store = TraceStore(root_dir=trace_root)
    for trace in traces:
        trace_store.append_raw_trace(trace, namespace="openclaw")

    traces_v1 = OpenClawTraceV1Adapter().adapt_events(
        scenario=scenario,
        events=events,
        session_id=run_result.session_id,
        agent_id=f"openclaw_{agent}",
        agent_config_id=agent,
        run_id=run_result.run_id,
        environment_id="openclaw_productivity_workspace",
    )
    for trace_v1, event in zip(traces_v1, events[: len(traces_v1)], strict=True):
        trace_store.append_trace_v1(trace_v1, namespace="openclaw")
        append_jsonl(
            REPO_ROOT / "data" / "intenttracebench_v0" / "benchmark_traces.jsonl",
            BenchmarkTraceRecord(
                trace=trace_v1,
                provenance=TraceSourceProvenance(
                    source_framework="openclaw",
                    source_type="live_openclaw",
                    source_run_id=run_result.run_id,
                    source_session_id=run_result.session_id,
                    source_event_id=event.source_event_id,
                    source_tool_call_id=event.source_tool_call_id,
                    source_transcript_path=str(run_result.transcript_path),
                    source_record_index=event.source_record_index,
                    agent_config_id=agent,
                    scenario_id=scenario.scenario_id,
                    run_index=1,
                ),
            ),
        )
    return {
        "ok": not errors,
        "errors": errors,
        "run": run_result.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in events],
        "trace_count": len(traces),
        "final_text": _read_final_text(run_result.transcript_path),
    }


def _read_final_text(transcript_path: Path) -> str | None:
    records = _load_jsonl(transcript_path)
    for record in reversed(records):
        message = record.get("message", {})
        if message.get("role") != "assistant":
            continue
        chunks = [
            str(content.get("text"))
            for content in message.get("content", [])
            if content.get("type") == "text" and content.get("text")
        ]
        if chunks:
            return "\n".join(chunks)
    return None


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    main()
