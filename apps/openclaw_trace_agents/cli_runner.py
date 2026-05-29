"""OpenClaw CLI runner.

This runner starts real OpenClaw agent turns and preserves the raw command artifacts.
It does not parse transcripts and does not call AgentGuard governance.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from agentguard.core.models import ScenarioRecord


class OpenClawRunResult(BaseModel):
    scenario_id: str
    agent_name: str
    session_id: str
    run_id: str | None = None
    returncode: int
    transcript_dir: Path | None = None
    transcript_path: Path | None = None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    timed_out: bool = False
    timeout_seconds: int | None = None


class OpenClawCliRunner:
    def __init__(
        self,
        output_root: Path = Path("data/openclaw_raw/runs"),
        profile: str | None = None,
        local: bool = True,
        timeout_seconds: int = 180,
    ):
        self.output_root = output_root
        self.profile = profile
        self.local = local
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        scenario: ScenarioRecord,
        agent_name: str = "main",
        run_index: int = 1,
    ) -> OpenClawRunResult:
        session_id = self._build_session_id(scenario.scenario_id, run_index)
        run_id = session_id
        run_dir = self.output_root / scenario.scenario_id / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        command = self._build_command(
            agent_name=agent_name,
            session_id=session_id,
            message=scenario.user_request,
        )
        (run_dir / "command.json").write_text(
            json.dumps({"command": command}, indent=2),
            encoding="utf-8",
        )

        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=Path.cwd(),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds + 15,
                check=False,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = 124
            stdout = _stream_to_text(exc.stdout)
            stderr = _stream_to_text(exc.stderr)

        stdout_path = run_dir / "stdout.json"
        stderr_path = run_dir / "stderr.txt"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

        transcript_path = self._session_path(session_id, agent_name)
        metadata = {
            "scenario_id": scenario.scenario_id,
            "agent_name": agent_name,
            "session_id": session_id,
            "run_id": run_id,
            "returncode": returncode,
            "timed_out": timed_out,
            "timeout_seconds": self.timeout_seconds,
            "transcript_path": str(transcript_path) if transcript_path.exists() else None,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        }
        (run_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return OpenClawRunResult(
            scenario_id=scenario.scenario_id,
            agent_name=agent_name,
            session_id=session_id,
            run_id=run_id,
            returncode=returncode,
            transcript_dir=transcript_path.parent if transcript_path.exists() else None,
            transcript_path=transcript_path if transcript_path.exists() else None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timed_out=timed_out,
            timeout_seconds=self.timeout_seconds,
        )

    def _build_command(self, agent_name: str, session_id: str, message: str) -> list[str]:
        command = ["openclaw"]
        if self.profile:
            command.extend(["--profile", self.profile])
        command.append("agent")
        if self.local:
            command.append("--local")
        if agent_name != "main":
            command.extend(["--agent", agent_name])
        command.extend(
            [
                "--session-id",
                session_id,
                "--message",
                message,
                "--json",
                "--timeout",
                str(self.timeout_seconds),
            ]
        )
        return command

    def _session_path(self, session_id: str, agent_name: str) -> Path:
        state_dir = Path.home() / (".openclaw" if self.profile is None else f".openclaw-{self.profile}")
        return state_dir / "agents" / agent_name / "sessions" / f"{session_id}.jsonl"

    def _build_session_id(self, scenario_id: str, run_index: int) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"agentguard_{scenario_id}_run_{run_index:03d}_{timestamp}_{uuid4().hex[:8]}"


def _stream_to_text(stream: str | bytes | None) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return stream
