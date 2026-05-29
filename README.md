# AgentGuard

AgentGuard is a trace-conditioned runtime governance layer for tool-using AI agents.

The Google hackathon demo centers on a Google ADK-style host agent. The research and
benchmarking pipeline can collect traces from OpenClaw and other agent runtimes through
the same adapter contract.

AgentGuard's central question is:

```text
Should this agent take this tool action now, for this user intent, after this trajectory?
```

That is different from only asking whether a tool call is generically safe.

## Repository Layout

```text
src/agentguard/              reusable AgentGuard framework and shared contracts
apps/google_adk_demo_agent/  hackathon-facing Google ADK host agent
apps/openclaw_trace_agents/  OpenClaw research trace-generation agents
data/scenarios/              benchmark and demo scenario JSONL files
data/traces/                 raw traces, labels, and guard outputs
data/seed_memory/            approved and blocked traces for retrieval
docs/                        architecture, delivery, and developer guides
scripts/                     command-line entrypoints for local workflows
tests/                       scaffold and contract validation tests
```

## Runtime Surfaces

AgentGuard has three runtime surfaces:

1. `apps/google_adk_demo_agent/`

   The hackathon demo host agent. This is where the Google ADK-facing experience should
   be implemented. It must route proposed tool calls through AgentGuard before execution.

2. `apps/openclaw_trace_agents/`

   Research trace collection. OpenClaw runs are not governed by AgentGuard here.
   OpenClaw transcripts/events are normalized into AgentGuard raw trace models for
   benchmark construction.

3. `src/agentguard/runtime/mock_runtime.py`

   Deterministic fallback runtime for tests, replay, and demos when live agent integration
   is unavailable.

## Core Runtime Flow

```text
User / Scenario
    -> Host Agent Runtime
    -> Proposed Tool Call
    -> Runtime Adapter
    -> ToolEventMapper
    -> TraceBuilder
    -> ToolInterceptor
    -> GuardEngine
    -> GuardDecision
    -> execute, skip, require approval, or block
    -> TraceStore
    -> Evaluation / Dashboard
```

No host agent should execute a consequential tool directly. Every proposed tool call must
be converted into a shared AgentGuard model and intercepted first.

That enforcement rule applies to AgentGuard-governed runtimes such as the Google ADK
demo. OpenClaw is different in this repository: it is used to collect real agent traces
offline, and AgentGuard decisions are generated later during benchmark evaluation.

## Main Components

| Component | Path | Purpose |
| --- | --- | --- |
| Shared contracts | `src/agentguard/core/` | Pydantic models, enums, config, and errors used by every subsystem. |
| Runtime adapters | `src/agentguard/runtime/` | Convert governed host runtime events into AgentGuard traces and enforce guard decisions. |
| Tracing | `src/agentguard/tracing/` | Build, serialize, validate, redact, and persist trace records. |
| Governance | `src/agentguard/governance/` | Evaluate traces and return allow/warn/review/block/approval decisions. |
| Evaluation | `src/agentguard/evaluation/` | Load scenarios and labels, replay traces, compare baselines, and compute metrics. |
| Dashboard | `src/agentguard/dashboard/` | Prepare demo-visible views for replay, verdicts, explanations, and metrics. |
| Google demo app | `apps/google_adk_demo_agent/` | Host agent for the Google hackathon submission. |
| OpenClaw trace agents | `apps/openclaw_trace_agents/` | Live-agent trace generation for research and benchmark datasets. |

See [docs/developer_runtime_guide.md](docs/developer_runtime_guide.md) for the detailed component guide.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The scripts also work before installing the package because they include a local bootstrap:

```bash
python3 scripts/run_mock_session.py
python3 scripts/run_dashboard.py
python3 scripts/collect_openclaw_traces.py
```

Real OpenClaw trace collection, after configuring an OpenClaw profile with a working
model provider key:

```bash
python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_DEFAULT_AGENT" \
  --scenario-file data/scenarios/email_intent_drift.jsonl \
  --runs-per-scenario 1
```

## Current Status

This is the initial development scaffold. Most modules intentionally contain deterministic
placeholder implementations so the team can start parallel work without changing shared
contracts.

## Development Rule

Do not pass loose runtime-specific dictionaries across subsystem boundaries. Convert host
agent events into the shared models in `src/agentguard/core/models.py` first.
