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
src/agentguard/server/       standalone AgentGuard server entry points
src/agentguard/sdk/          public agent-integration client boundary
src/agentguard/integrations/ framework-specific integration packages
src/agentguard/firewall_v2/  reusable AgentGuard enforcement engine
services/agentguard_api/     deployable AgentGuard service boundary
apps/agentguard_dashboard/   standalone AgentGuard product dashboard boundary
examples/google_adk_agent/   independent Google ADK example consumer
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
    -> optional AgentGuardFirewallV2 tiered evaluation
    -> TraceFeatureV1
    -> GuardScoreV1
    -> GuardDecisionV1
    -> SessionRiskStateV1
    -> runtime allow / require_approval / block
```

The canonical schema is documented in [schema_architecture.md](schema_architecture.md)
and implemented in [src/agentguard/tracing/schema_v1.py](src/agentguard/tracing/schema_v1.py).

## Runtime Surfaces

1. `services/agentguard_api/`

   The standalone AgentGuard product API, served by `agentguard.server.app:app`.

2. `examples/google_adk_agent/`

   An independent Google ADK personal-agent example. It consumes the public
   `agentguard.integrations.google_adk` boundary and owns the ADK agent implementation.

3. `apps/agentguard_dashboard/`

   The standalone AgentGuard product UI and React implementation.

4. `apps/openclaw_trace_agents/`

   Historical trace generation. OpenClaw is not guarded during collection. Its
   transcripts are converted into canonical `AgentGuardTraceV1` records so the project
   can build a benchmark dataset from realistic agent behavior.

5. `src/agentguard/`

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
| Server entry point | `src/agentguard/server/app.py` | Stable ASGI boundary for standalone AgentGuard deployments. |
| SDK client | `src/agentguard/sdk/client.py` | Framework-independent evaluation client protocol and current in-process client. |
| Google ADK integration | `src/agentguard/integrations/google_adk/` | ADK trace session, MCP registry, metadata mapping, runtime policy mapping, and lifecycle events. |
| FirewallV2 tiers | `src/agentguard/firewall_v2/tiers/` | Tier 1 deterministic policy, Tier 2 boundary, and Gemini-backed Tier 3 judge evidence. |
| V2 combiner | `src/agentguard/firewall_v2/enforcement/combiner.py` | Deterministically combines tier recommendations without allowing Tier 3 to weaken hard policy. |
| V1 feature builder | `src/agentguard/governance/feature_builder_v1.py` | Derives policy/context/retrieval/statistical feature records from traces. |
| V1 scoring | `src/agentguard/governance/scoring_v1.py` | Computes step and cumulative risk scores with placeholder formulas. |
| V1 decision policy | `src/agentguard/governance/decision_policy_v1.py` | Maps scores and hard policy signals to verdicts. |
| V1 firewall | `src/agentguard/governance/firewall_v1.py` | Orchestrates trace persistence, feature extraction, scoring, decisioning, live events, and session risk. |
| Evaluation | `src/agentguard/evaluation/` | Dataset models, labels, metrics, replay, and baseline guard entrypoints. |
| Product dashboard | `apps/agentguard_dashboard/` | React UI for agents, live interception, replay, memory, operations, and Guard Admin. |

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python3 -m pytest
```

The base `agentguard` installation does not require Google ADK. Agent developers can
install only the integration they need:

```bash
pip install -e ".[adk,gemini]"
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
cd apps/agentguard_dashboard
npm install
cd ../..
```

Start the FastAPI backend and React dashboard together:

```bash
make demo
```

Open `http://127.0.0.1:5173`. The deterministic local dataset is initialized
automatically and does not require Gemini, Gmail, Docker, or Elastic credentials.

For the live ADK/V2 Tier 3 path, configure:

```bash
GOOGLE_API_KEY=...
AGENTGUARD_FIREWALL_MODE=v2
AGENTGUARD_TIER_1_ENABLED=true
AGENTGUARD_AGENTTRUST_SHELL_ENABLED=true
AGENTGUARD_INTENT_LLM_ENABLED=true
AGENTGUARD_INTENT_MODEL=gemini-2.5-flash
AGENTGUARD_TIER_3_ENABLED=true
AGENTGUARD_TIER3_ENFORCEMENT_ENABLED=true
```

FirewallV2 extracts one schema-validated intent contract when the ADK user turn
starts. Every tool proposal from that turn references the same `intent_id`. Gemini
structured output is the primary extractor; if it is unavailable, explicit actions
and constraints are extracted with a conservative deterministic fallback.

For central team testing, set `AGENTGUARD_MOCK_PIPELINE_ONLY=true` so the guard
pipeline logs decisions without executing tools.

Reset the demo dataset:

```bash
make demo-data
```

Verify both applications:

```bash
make test
make build-frontend
```

Run the pinned 300-case AgentTrust shell-security benchmark:

```bash
python scripts/run_agenttrust_benchmark.py
```

The production report uses the same stateless Tier 1 path as live ADK calls. The
optional `--benchmark-compatibility-rules` flag enables upstream benchmark-only rules
and is labeled separately in the generated report. The default `--scope shell`
evaluates 254 shell-compatible scenarios; use `--scope all` only to intentionally
project all 300 upstream cases through the shell interception path.

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

## Central Team Deployment

The simplest hosted setup is two Render services:

```text
agentguard-api  FastAPI web service
agentguard-web  React/Vite static site
```

Backend start command:

```bash
python -m uvicorn agentguard.server.app:app --host 0.0.0.0 --port $PORT
```

Frontend settings:

```text
Root directory: apps/agentguard_dashboard
Build command: npm install && npm run build
Publish directory: dist
```

Add a static-site rewrite from `/api/*` to the backend `/api/*`, then add the SPA
fallback from `/*` to `/index.html`. Keep `AGENTGUARD_MOCK_PIPELINE_ONLY=true` for
shared testing unless the deployment is intentionally allowed to execute tools.

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
