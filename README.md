# AgentGuard

AgentGuard is a trace-conditioned runtime governance layer for tool-using AI agents.

The project asks one practical question before every consequential tool call:

```text
Should this agent take this tool action now, for this user intent, after this trajectory?
```

The current implementation uses a canonical v1 schema, a deterministic v1 firewall
pipeline, active Google ADK callback interception, and a verified Elastic Cloud storage
path. Deeper statistical retrieval is being built on top of this working skeleton.

## Repository Layout

```text
src/agentguard/              reusable AgentGuard framework
apps/adk_agent/              guarded Google ADK terminal assistant
apps/web/                    AgentGuard product dashboard
apps/openclaw_trace_agents/  OpenClaw historical trace-generation pipeline
data/scenarios/              benchmark and demo scenario JSONL files
data/elastic/                Elastic database workspace: mappings, query bodies, notebooks, exports
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
    -> runtime allow / require_approval
```

The canonical schema is documented in [schema_architecture.md](schema_architecture.md)
and implemented in [src/agentguard/tracing/schema_v1.py](src/agentguard/tracing/schema_v1.py).

## Runtime Surfaces

1. `apps/adk_agent/`

   The governed Google ADK runtime. ADK tool callbacks build `AgentGuardTraceV1`
   records, call `AgentGuardFirewallV1` before execution, and expose only two runtime
   policies for now: `allow` and `require_approval`.

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
| Google ADK adapter | `src/agentguard/runtime/google_adk_adapter.py` | Live ADK trace session, tool metadata mapping, firewall call, runtime policy mapping, and lifecycle events. |
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
.venv/bin/python -m pytest tests/test_google_adk_runtime.py
python3 scripts/collect_openclaw_traces.py
```

## Product Demo

Install the frontend once:

```bash
cd apps/web
npm install
cd ../..
```

Start the FastAPI backend and React dashboard together:

```bash
make demo
```

Open `http://127.0.0.1:5173`. The deterministic local dataset is initialized
automatically and does not require Gemini, Gmail, Docker, or Elastic credentials.

Reset the demo dataset:

```bash
make demo-data
```

Verify both applications:

```bash
make test
make build-frontend
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

## Elastic Storage

Elastic integration starts with canonical v1 traces:

```bash
python3 scripts/ingest_openclaw_traces_to_elastic.py --dry-run
```

After setting `ELASTICSEARCH_URL` and auth in an env file:

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/setup_elastic_indices.py
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/ingest_openclaw_traces_to_elastic.py
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/replay_traces.py --elastic --namespace openclaw_replay
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/query_elastic_traces.py --size 5
```

See [docs/elastic_storage.md](docs/elastic_storage.md).

The database workspace lives under [data/elastic](data/elastic). It contains checked-in
mapping snapshots, reusable query bodies, database inspection notebooks, and ignored
local exports. The actual Elastic connector code remains under `src/agentguard/storage`.

Current verified checkpoint:

```text
7 OpenClaw traces indexed into agentguard-traces-v1
7 replayed guard decisions indexed into agentguard-guard-decisions-v1
21 live events indexed into agentguard-live-events-v1
4 session-risk states indexed into agentguard-session-risk-v1
```

## Current Status

The repository has a working v1 trace and firewall path with deterministic placeholder
logic. Local JSONL storage and Elastic Cloud storage are both running; Elastic is now the
planned production memory and retrieval backend described in
[schema_architecture.md](schema_architecture.md).

Detailed current state is tracked in
[src/agentguard/current_state_of_developement.md](src/agentguard/current_state_of_developement.md).

## Development Rule

Do not pass runtime-specific dictionaries across subsystem boundaries. Convert host
runtime events into `AgentGuardTraceV1` first, then run `AgentGuardFirewallV1`.
