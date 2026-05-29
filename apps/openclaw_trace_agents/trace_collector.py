"""OpenClaw trace collection pipeline for benchmark dataset construction."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from agentguard.core.models import RawTraceRecord, ScenarioRecord
from agentguard.evaluation.dataset_models import BenchmarkTraceRecord, TraceSourceProvenance
from agentguard.tracing.serializers import append_jsonl
from agentguard.tracing.trace_store import TraceStore
from apps.openclaw_trace_agents.base import OpenClawTraceAgent
from apps.openclaw_trace_agents.cli_runner import OpenClawCliRunner, OpenClawRunResult
from apps.openclaw_trace_agents.event_normalizer import OpenClawEventNormalizer
from apps.openclaw_trace_agents.transcript_reader import OpenClawTranscriptReader


class OpenClawTraceCollector:
    """Collect raw tool-use traces from OpenClaw agents.

    This collector is intentionally one-way: it observes OpenClaw behavior and writes
    AgentGuard RawTraceRecord objects. It does not run AgentGuard governance and does not
    alter OpenClaw execution.
    """

    def __init__(
        self,
        agent_registry: dict[str, OpenClawTraceAgent],
        trace_store: TraceStore | None = None,
        normalizer: OpenClawEventNormalizer | None = None,
        max_steps: int = 20,
    ):
        self.agent_registry = agent_registry
        self.trace_store = trace_store or TraceStore()
        self.normalizer = normalizer or OpenClawEventNormalizer()
        self.max_steps = max_steps

    def collect_scenario(self, scenario: ScenarioRecord) -> list[RawTraceRecord]:
        agent = self.agent_registry.get(scenario.domain)
        if agent is None:
            raise ValueError(f"No OpenClaw trace agent registered for domain: {scenario.domain}")

        events = agent.propose_tool_events(scenario)
        traces = self.normalizer.normalize_events(
            agent_id=agent.agent_id,
            domain=agent.domain,
            scenario=scenario,
            events=events,
            max_steps=self.max_steps,
        )
        for trace in traces:
            self.trace_store.append_raw_trace(trace, namespace="openclaw")
        return traces


def raw_artifact_dir(root: Path, scenario_id: str) -> Path:
    return root / "openclaw_raw" / "runs" / scenario_id


class RealOpenClawTraceCollector:
    """Run real OpenClaw sessions and normalize their transcript tool calls."""

    def __init__(
        self,
        cli_runner: OpenClawCliRunner,
        transcript_reader: OpenClawTranscriptReader | None = None,
        normalizer: OpenClawEventNormalizer | None = None,
        trace_store: TraceStore | None = None,
        openclaw_raw_root: Path = Path("data/openclaw_raw"),
        benchmark_record_path: Path = Path("data/intenttracebench_v0/benchmark_traces.jsonl"),
        max_steps: int = 20,
    ):
        self.cli_runner = cli_runner
        self.transcript_reader = transcript_reader or OpenClawTranscriptReader()
        self.normalizer = normalizer or OpenClawEventNormalizer()
        self.trace_store = trace_store or TraceStore()
        self.openclaw_raw_root = openclaw_raw_root
        self.benchmark_record_path = benchmark_record_path
        self.max_steps = max_steps

    def collect_scenario(
        self,
        scenario: ScenarioRecord,
        agent_name: str = "main",
        run_index: int = 1,
    ) -> list[RawTraceRecord]:
        run_result = self.cli_runner.run(
            scenario=scenario,
            agent_name=agent_name,
            run_index=run_index,
        )
        if run_result.transcript_path is None:
            raise RuntimeError(
                "OpenClaw did not produce a session transcript. "
                f"returncode={run_result.returncode}; timed_out={run_result.timed_out}; "
                f"stderr={run_result.stderr_path}"
            )

        preserved_transcript = self._preserve_transcript(run_result)
        events = self.transcript_reader.read_tool_events(preserved_transcript)
        if not events:
            model_errors = self.transcript_reader.read_model_errors(preserved_transcript)
            if model_errors:
                raise RuntimeError(
                    "OpenClaw transcript contained a model error before any tool calls. "
                    f"errors={model_errors}; transcript={preserved_transcript}; "
                    f"stdout={run_result.stdout_path}; stderr={run_result.stderr_path}"
                )
            raise RuntimeError(
                "OpenClaw transcript contained no tool calls. "
                f"transcript={preserved_transcript}; stdout={run_result.stdout_path}; "
                f"stderr={run_result.stderr_path}"
            )

        traces = self.normalizer.normalize_events(
            agent_id=f"openclaw_{agent_name}",
            domain=scenario.domain,
            scenario=scenario,
            events=events,
            max_steps=self.max_steps,
            session_id=run_result.session_id,
        )
        for trace, event in zip(traces, events[: len(traces)], strict=True):
            self.trace_store.append_raw_trace(trace, namespace="openclaw")
            append_jsonl(
                self.benchmark_record_path,
                BenchmarkTraceRecord(
                    trace=trace,
                    provenance=TraceSourceProvenance(
                        source_framework="openclaw",
                        source_type="live_openclaw",
                        source_run_id=run_result.run_id,
                        source_session_id=run_result.session_id,
                        source_event_id=event.source_event_id,
                        source_tool_call_id=event.source_tool_call_id,
                        source_transcript_path=str(preserved_transcript),
                        source_record_index=event.source_record_index,
                        agent_config_id=agent_name,
                        scenario_id=scenario.scenario_id,
                        run_index=run_index,
                    ),
                ),
            )
        self._write_normalized_event_summary(scenario, run_result, events)
        return traces

    def _preserve_transcript(self, run_result: OpenClawRunResult) -> Path:
        if run_result.transcript_path is None:
            raise ValueError("run_result.transcript_path is required")
        target_dir = (
            self.openclaw_raw_root
            / "transcripts"
            / run_result.scenario_id
            / str(run_result.run_id)
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / "session.jsonl"
        shutil.copyfile(run_result.transcript_path, target_path)
        return target_path

    def _write_normalized_event_summary(
        self,
        scenario: ScenarioRecord,
        run_result: OpenClawRunResult,
        events,
    ) -> None:
        output_dir = (
            self.openclaw_raw_root
            / "normalized_events"
            / scenario.scenario_id
            / str(run_result.run_id)
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "events.jsonl"
        with output_path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(event.model_dump_json())
                handle.write("\n")
        metadata = {
            "scenario_id": scenario.scenario_id,
            "run_id": run_result.run_id,
            "session_id": run_result.session_id,
            "event_count": len(events),
            "openclaw_returncode": run_result.returncode,
            "openclaw_timed_out": run_result.timed_out,
        }
        (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
