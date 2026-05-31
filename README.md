# AgentGuard

AgentGuard is a trace-conditioned runtime governance layer for tool-using AI agents.

The project asks one practical question before every consequential tool call:

```text
Should this agent take this tool action now, for this user intent, after this trajectory?
```

The current implementation uses a canonical v1 schema and a deterministic v1 firewall
pipeline. Deeper statistical retrieval, Elastic-backed memory, and Google ADK runtime
interception are being built on top of this working skeleton.

## Repository Layout

```text
src/agentguard/              reusable AgentGuard framework
apps/google_adk_demo_agent/  hackathon-facing Google ADK demo path
apps/openclaw_trace_agents/  OpenClaw historical trace-generation pipeline
data/scenarios/              benchmark and demo scenario JSONL files
data/traces/                 local JSONL trace, feature, score, decision, and event stores
data/openclaw_raw/           raw OpenClaw run artifacts and transcript samples
data/intenttracebench_v0/    benchmark-ready trace dataset artifacts
docs/                        current architecture and developer guides
scripts/                     command-line entrypoints for local workflows
tests/                       schema, adapter, collector, and firewall tests
```

## Implemented Runtime Flow

```text
Runtime-specific proposed tool call
    -> runtime adapter or trace adapter
    -> AgentGuardTraceV1
    -> AgentGuardFirewallV1
    -> TraceFeatureV1
    -> GuardScoreV1
    -> GuardDecisionV1
    -> SessionRiskStateV1
    -> allow / warn / review / require_approval / block
```

The canonical schema is documented in [schema_architecture.md](schema_architecture.md)
and implemented in [src/agentguard/tracing/schema_v1.py](src/agentguard/tracing/schema_v1.py).

## Runtime Surfaces

1. `apps/google_adk_demo_agent/`

   The hackathon-facing governed runtime. The current local demo builds an
   `AgentGuardTraceV1` and sends it through `AgentGuardFirewallV1`. The full Google ADK
   MCP interception adapter is the next integration step.

2. `apps/openclaw_trace_agents/`

   Historical trace generation. OpenClaw is not guarded during collection. Its
   transcripts are converted into canonical `AgentGuardTraceV1` records so the project
   can build a benchmark dataset from realistic agent behavior.

3. `src/agentguard/`

   The reusable guard library: schemas, adapters, v1 firewall, tool metadata, local
   trace store, replay, and evaluation scaffolding.

## Main Components

| Component | Path | Purpose |
| --- | --- | --- |
| Canonical v1 schema | `src/agentguard/tracing/schema_v1.py` | Shared trace, feature, score, decision, session-risk, label, and scenario models. |
| V1 trace builder | `src/agentguard/tracing/trace_v1_builder.py` | Builds canonical traces from runtime inputs. |
| OpenClaw adapter | `src/agentguard/tracing/adapters/openclaw_trace_adapter.py` | Converts OpenClaw tool events into `AgentGuardTraceV1`. |
| Trace store | `src/agentguard/tracing/trace_store.py` | Persists v1 traces, features, scores, decisions, live events, labels, and session state to local JSONL/JSON. |
| Tool registry | `src/agentguard/runtime/tool_registry.py` | Stores tool domain, side-effect, confirmation, and risk metadata. |
| Google ADK adapter | `src/agentguard/runtime/google_adk_adapter.py` | Placeholder for live ADK/MCP interception; currently documents the expected v1 integration point. |
| V1 feature builder | `src/agentguard/governance/feature_builder_v1.py` | Derives policy/context/retrieval/statistical feature records from traces. |
| V1 scoring | `src/agentguard/governance/scoring_v1.py` | Computes step and cumulative risk scores with placeholder formulas. |
| V1 decision policy | `src/agentguard/governance/decision_policy_v1.py` | Maps scores and hard policy signals to verdicts. |
| V1 firewall | `src/agentguard/governance/firewall_v1.py` | Orchestrates trace persistence, feature extraction, scoring, decisioning, live events, and session risk. |
| Evaluation | `src/agentguard/evaluation/` | Dataset models, labels, metrics, replay, and baseline guard entrypoints. |
| Dashboard | `src/agentguard/dashboard/` | Lightweight view helpers for demo/replay surfaces. |

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python3 -m pytest
```

The scripts also work before package installation because they include a local bootstrap:

```bash
python3 scripts/run_mock_session.py
PYTHONPATH=src python3 apps/google_adk_demo_agent/run_demo.py
python3 scripts/collect_openclaw_traces.py
```

## OpenClaw Productivity Agent

Set up the controlled OpenClaw productivity agent:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/setup_openclaw_productivity_agent.py
```

Run real OpenClaw trace collection:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_PRODUCTIVITY_AGENT" \
  --scenario-file data/scenarios/productivity_agent_scenarios.jsonl \
  --runs-per-scenario 1 \
  --timeout-seconds 180
```

Inspect and interact with the virtual email/file/calendar environment:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

Open `http://127.0.0.1:8765`.

## Current Status

The repository has a working v1 trace and firewall path with deterministic placeholder
logic. Local JSONL storage is implemented now; Elastic is the planned production memory
and retrieval backend described in [schema_architecture.md](schema_architecture.md).

Detailed current state is tracked in
[src/agentguard/current_state_of_developement.md](src/agentguard/current_state_of_developement.md).

## Development Rule

Do not pass runtime-specific dictionaries across subsystem boundaries. Convert host
runtime events into `AgentGuardTraceV1` first, then run `AgentGuardFirewallV1`.
