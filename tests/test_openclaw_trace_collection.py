from pathlib import Path

from apps.openclaw_trace_agents.run_trace_collection import collect_traces
from apps.openclaw_trace_agents.cli_runner import OpenClawRunResult
from apps.openclaw_trace_agents.trace_collector import RealOpenClawTraceCollector
from agentguard.evaluation.scenarios import load_scenarios
from agentguard.tracing.validators import validate_raw_trace_file


def test_openclaw_trace_collection_writes_only_raw_dataset_traces(tmp_path):
    scenario_file = Path("data/scenarios/email_intent_drift.jsonl")

    trace_count = collect_traces([scenario_file], trace_root=tmp_path)

    raw_path = tmp_path / "raw" / "openclaw" / "traces.jsonl"
    guard_path = tmp_path / "guard_outputs" / "decisions.jsonl"
    traces = validate_raw_trace_file(raw_path)

    assert trace_count >= 1
    assert len(traces) == trace_count
    assert not guard_path.exists()
    assert traces[0].agent_framework == "openclaw"
    assert traces[-1].proposed_tool_call.tool_name == "gmail_send"


class FakeOpenClawCliRunner:
    def __init__(self, transcript_path: Path):
        self.transcript_path = transcript_path

    def run(self, scenario, agent_name: str = "main", run_index: int = 1):
        return OpenClawRunResult(
            scenario_id=scenario.scenario_id,
            agent_name=agent_name,
            session_id=f"agentguard_{scenario.scenario_id}_run_{run_index:03d}",
            run_id=f"agentguard_{scenario.scenario_id}_run_{run_index:03d}",
            returncode=0,
            transcript_dir=self.transcript_path.parent,
            transcript_path=self.transcript_path,
            stdout_path=self.transcript_path,
            stderr_path=self.transcript_path,
        )


def test_real_openclaw_collector_parses_transcript_and_writes_benchmark_records(tmp_path):
    scenario = load_scenarios("data/scenarios/file_scope_creep.jsonl")[0]
    transcript_path = Path("data/openclaw_raw/samples/openclaw_session_tool_call_sample.jsonl")
    collector = RealOpenClawTraceCollector(
        cli_runner=FakeOpenClawCliRunner(transcript_path),
        trace_store=None,
        openclaw_raw_root=tmp_path / "openclaw_raw",
        benchmark_record_path=tmp_path / "intenttracebench_v0" / "benchmark_traces.jsonl",
    )
    collector.trace_store.root_dir = tmp_path / "traces"

    traces = collector.collect_scenario(scenario=scenario, agent_name="main", run_index=1)

    assert len(traces) == 2
    assert traces[0].source_type == "live_openclaw"
    assert (tmp_path / "traces" / "raw" / "openclaw" / "traces.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "openclaw" / "traces.jsonl").exists()
    assert (
        tmp_path
        / "openclaw_raw"
        / "transcripts"
        / scenario.scenario_id
        / f"agentguard_{scenario.scenario_id}_run_001"
        / "session.jsonl"
    ).exists()
    assert (tmp_path / "intenttracebench_v0" / "benchmark_traces.jsonl").exists()
