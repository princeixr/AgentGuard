"""Collect benchmark raw traces from OpenClaw trace agents."""

from __future__ import annotations

import argparse
from pathlib import Path

from agentguard.evaluation.scenarios import load_scenarios
from agentguard.tracing.trace_store import TraceStore
from apps.openclaw_trace_agents.cli_runner import OpenClawCliRunner
from apps.openclaw_trace_agents.calendar_agent import build_calendar_agent
from apps.openclaw_trace_agents.email_agent import build_email_agent
from apps.openclaw_trace_agents.file_agent import build_file_agent
from apps.openclaw_trace_agents.trace_collector import OpenClawTraceCollector, RealOpenClawTraceCollector


def build_default_agent_registry() -> dict:
    agents = [
        build_email_agent(),
        build_file_agent(),
        build_calendar_agent(),
    ]
    return {agent.domain: agent for agent in agents}


def collect_traces(
    scenario_files: list[Path],
    trace_root: Path = Path("data/traces"),
) -> int:
    collector = OpenClawTraceCollector(
        agent_registry=build_default_agent_registry(),
        trace_store=TraceStore(root_dir=trace_root),
    )

    trace_count = 0
    for scenario_file in scenario_files:
        for scenario in load_scenarios(scenario_file):
            trace_count += len(collector.collect_scenario(scenario))
    return trace_count


def collect_real_openclaw_traces(
    scenario_files: list[Path],
    trace_root: Path = Path("data/traces"),
    openclaw_raw_root: Path = Path("data/openclaw_raw"),
    agent_name: str = "main",
    profile: str | None = None,
    runs_per_scenario: int = 1,
    timeout_seconds: int = 180,
    max_steps: int = 20,
) -> int:
    collector = RealOpenClawTraceCollector(
        cli_runner=OpenClawCliRunner(
            output_root=openclaw_raw_root / "runs",
            profile=profile,
            timeout_seconds=timeout_seconds,
        ),
        trace_store=TraceStore(root_dir=trace_root),
        openclaw_raw_root=openclaw_raw_root,
        max_steps=max_steps,
    )

    trace_count = 0
    for scenario_file in scenario_files:
        for scenario in load_scenarios(scenario_file):
            for run_index in range(1, runs_per_scenario + 1):
                trace_count += len(
                    collector.collect_scenario(
                        scenario=scenario,
                        agent_name=agent_name,
                        run_index=run_index,
                    )
                )
    return trace_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario-file",
        action="append",
        type=Path,
        help="Scenario JSONL file. Defaults to every file in data/scenarios.",
    )
    parser.add_argument(
        "--trace-root",
        type=Path,
        default=Path("data/traces"),
        help="Root trace output directory.",
    )
    parser.add_argument(
        "--real-openclaw",
        action="store_true",
        help="Run real OpenClaw CLI sessions instead of deterministic fixture agents.",
    )
    parser.add_argument(
        "--agent",
        default="main",
        help="OpenClaw agent id for --real-openclaw. Defaults to main.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="OpenClaw profile for --real-openclaw, e.g. agentguard.",
    )
    parser.add_argument(
        "--runs-per-scenario",
        type=int,
        default=1,
        help="Number of OpenClaw runs per scenario in --real-openclaw mode.",
    )
    parser.add_argument(
        "--openclaw-raw-root",
        type=Path,
        default=Path("data/openclaw_raw"),
        help="Directory for raw OpenClaw stdout/stderr/transcripts/normalized events.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="Timeout for each OpenClaw agent run.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum tool calls to normalize from each session.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario_files = args.scenario_file or sorted(Path("data/scenarios").glob("*.jsonl"))
    if args.real_openclaw:
        trace_count = collect_real_openclaw_traces(
            scenario_files=scenario_files,
            trace_root=args.trace_root,
            openclaw_raw_root=args.openclaw_raw_root,
            agent_name=args.agent,
            profile=args.profile,
            runs_per_scenario=args.runs_per_scenario,
            timeout_seconds=args.timeout_seconds,
            max_steps=args.max_steps,
        )
        mode = "real OpenClaw"
    else:
        trace_count = collect_traces(
            scenario_files=scenario_files,
            trace_root=args.trace_root,
        )
        mode = "fixture"
    print(
        f"Collected {trace_count} {mode} trace(s) from {len(scenario_files)} "
        "scenario file(s)."
    )


if __name__ == "__main__":
    main()
