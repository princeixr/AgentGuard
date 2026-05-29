# AgentGuard Developer Runtime Guide

This guide explains the current repository structure, the purpose of each component,
and how data should move through the system. It is written for developers joining the
project after the initial scaffold.

## Project Goal

AgentGuard is a runtime governance layer for tool-using AI agents. It intercepts proposed
tool calls before execution, builds a session-aware trace, evaluates the action against
user intent and prior trajectory, and returns a governance decision.

The project has two public-facing goals:

1. A Google hackathon demo where AgentGuard governs a Google ADK-style host agent.
2. A research benchmark pipeline where OpenClaw agents generate raw traces for evaluation.

The shared core must remain runtime-agnostic. Google ADK, OpenClaw, mock runtimes, and
future host agents must all emit the same AgentGuard models.

## End-to-End Governed Runtime

```text
Scenario or user request
    -> Host agent runtime
    -> Proposed tool call
    -> Runtime adapter
    -> ToolEventMapper
    -> ProposedToolCall
    -> TraceBuilder
    -> RawTraceRecord
    -> ToolInterceptor
    -> GuardEngine
    -> GuardDecision
    -> Runtime enforcement
    -> ExecutedToolCall or skipped/blocked record
    -> TraceStore
    -> Evaluation, replay, dashboard, reports
```

The most important rule is simple: no consequential tool should execute before AgentGuard
has seen the proposed call and returned a decision.

This is the Google ADK demo path. OpenClaw trace generation uses a different offline
collection path and should not call AgentGuard governance during collection.

## OpenClaw Dataset Collection Flow

```text
Scenario JSONL
    -> real OpenClaw agent config
    -> OpenClaw run
    -> transcript.jsonl or event stream
    -> OpenClaw transcript reader / CLI runner
    -> OpenClaw event normalizer
    -> RawTraceRecord
    -> data/traces/raw/openclaw/
    -> labels, splits, guard outputs later
```

OpenClaw traces are evidence for benchmark construction. They are not runtime enforcement
events.

## Data Contracts

All major subsystem boundaries use models from `src/agentguard/core/models.py`.

| Model | Purpose |
| --- | --- |
| `UserIntent` | Root context for the user's request, allowed tools, disallowed tools, and approval requirements. |
| `ProposedToolCall` | Tool call before execution. Created by runtime mapping code. |
| `ExecutedToolCall` | Tool result or skipped/blocked/failure record after enforcement. |
| `ToolOutputContext` | Signals from prior tool output, including untrusted instructions or secret-like content. |
| `RawTraceRecord` | What happened and what was visible to the agent. No labels or guard scores. |
| `LabelRecord` | Gold labels and rationales used by evaluation. Stored separately from raw traces. |
| `GuardDecision` | The governance output: verdict, risk score, latency, and explanation. |
| `ScenarioRecord` | Scenario JSONL contract used by benchmark and demo runners. |
| `MetricReport` | Aggregate evaluation metrics. |
| `DemoReport` | Demo/report artifact wrapper. |

Raw traces, labels, and guard outputs must remain separate:

```text
data/traces/raw/
data/traces/labeled/
data/traces/guard_outputs/
```

This separation prevents benchmark contamination.

## Component Guide

### `src/agentguard/core/`

Core is the shared contract layer. It should be stable and conservative.

Files:

```text
enums.py    Verdict, FailureType, ToolRiskLevel
models.py   Pydantic models used across all subsystems
config.py   Local configuration object
errors.py   Shared exception types
```

Developer rule: if you change a model or enum here, every track may be affected. Treat
changes to this directory as interface changes.

### `src/agentguard/runtime/`

Runtime is responsible for adapting host agents into AgentGuard's model world.

Files:

```text
runtime_adapter.py       Protocol all runtimes must satisfy
google_adk_adapter.py    Google hackathon runtime adapter placeholder
openclaw_adapter.py      Deprecated placeholder; OpenClaw is a dataset source, not an enforced runtime
mock_runtime.py          Deterministic runtime for tests and fallback demos
interceptor.py           Calls GuardEngine.evaluate(trace)
tool_event_mapper.py     Converts host runtime events into ProposedToolCall
tool_registry.py         Registers tools and risk metadata
tool_executor.py         Executes approved tools and returns ExecutedToolCall
mock_tools/              Safe email, file, and calendar mock tools
```

Runtime owns:

- capturing proposed tool calls,
- mapping runtime-specific events,
- building raw traces,
- calling the interceptor,
- enforcing guard decisions,
- recording executed, skipped, blocked, or failed calls.

Runtime must not:

- leak Google ADK or OpenClaw objects into governance,
- execute tools before interception,
- store labels or evaluation metrics.

### `src/agentguard/tracing/`

Tracing owns trace construction, persistence, validation, serialization, and redaction.

Files:

```text
trace_builder.py   Builds RawTraceRecord objects
trace_store.py     Appends raw traces, labels, and guard decisions to JSONL
serializers.py     JSONL helpers
validators.py      Loads and validates stored artifacts
redaction.py       Minimal public-release redaction helpers
```

Tracing is intentionally boring. It should be reliable, schema-valid, and easy to inspect.

### `src/agentguard/governance/`

Governance answers:

```text
Should this agent take this action now?
```

Files:

```text
guard_engine.py      Orchestrates the full decision pipeline
static_policy.py     Fast hard checks and obvious violations
retrieval.py         Approved/blocked trace retrieval interface
scoring.py           Trajectory risk scoring
decision_policy.py   Maps risk and policy triggers into a verdict
explanations.py      Short human-readable explanations
```

Current modes:

```text
rule_only
stateless_intent
full_agentguard
```

Governance consumes `RawTraceRecord` and emits `GuardDecision`. It must not depend on
Google ADK, OpenClaw, dashboard code, or runtime-specific objects.

### `src/agentguard/evaluation/`

Evaluation proves whether trajectory-aware governance improves over stateless baselines.

Files:

```text
scenarios.py        Scenario loading and BenchmarkRunner
labels.py           Label loading and validation
baseline_guards.py  Required guard baseline factory
metrics.py          Accuracy, recall, false positive rate, macro-F1, latency
replay.py           Re-runs guards over stored traces
reports.py          Demo and benchmark report helpers
```

Evaluation should compare guard decisions against labels using the same raw traces.
This is why replay exists: each baseline should see identical trace inputs.

### `src/agentguard/dashboard/`

Dashboard is for demo-visible interpretation, not core guard logic.

Files:

```text
app.py          Placeholder dashboard entrypoint
components.py   Small view component helpers
views.py        View-model builders for replay and verdict displays
```

Dashboard should read persisted traces, labels, and guard outputs. It should not call
live runtimes directly in the first implementation.

## Host Applications

### `apps/google_adk_demo_agent/`

This is the hackathon-facing app. It should be the primary demo surface.

Files:

```text
agent.py      Google ADK agent construction placeholder
tools.py      Tool registry for email demo tools
run_demo.py   Runnable local demo path using the mock runtime for now
README.md     App-specific notes
```

Expected final behavior:

```text
Google ADK agent proposes tool call
    -> google_adk_adapter maps event
    -> AgentGuard evaluates
    -> allowed call executes, risky call halts or requires approval
```

### `apps/openclaw_trace_agents/`

This is the research trace-generation area. OpenClaw is used to generate raw benchmark
data, not to test AgentGuard runtime enforcement.

Files:

```text
configs/                  Planned real OpenClaw agent configurations
cli_runner.py             Planned real OpenClaw CLI runner
transcript_reader.py      Planned parser for OpenClaw transcript.jsonl files
event_normalizer.py       Converts OpenClaw tool events into RawTraceRecord
trace_collector.py        Orchestrates collection and persistence
email_agent.py            Temporary email fixture for collector tests
file_agent.py             Temporary file fixture for collector tests
calendar_agent.py         Temporary calendar fixture for collector tests
run_trace_collection.py   Trace collection entrypoint
README.md                 App-specific notes
```

Expected final behavior:

```text
OpenClaw agent runs with configured tools
    -> transcript or event stream is captured
    -> transcript_reader / cli_runner extracts tool events
    -> event_normalizer maps events
    -> RawTraceRecord is persisted under data/traces/raw/openclaw/
    -> labels and guard outputs are generated separately
```

OpenClaw is not the hackathon story's primary runtime and should not be intercepted by
AgentGuard during collection. It is the research dataset source.

## Data Directories

### `data/scenarios/`

Scenario JSONL files used by mock runs, benchmarks, and demo planning.

Current files:

```text
email_intent_drift.jsonl
file_scope_creep.jsonl
prompt_injection.jsonl
calendar_premature_action.jsonl
clean_sessions.jsonl
```

### `data/seed_memory/`

Seed retrieval records for similar approved and blocked traces.

```text
approved_traces.jsonl
blocked_traces.jsonl
```

These are not labels. They are memory examples used by retrieval.

### `data/traces/`

Generated artifacts.

```text
raw/google_adk/      Raw traces from Google demo agents
raw/openclaw/        Raw traces from OpenClaw trace agents
raw/mock/            Raw traces from deterministic mock runtime
raw/synthetic/       Synthetic/adapted traces
labeled/             LabelRecord JSONL files
guard_outputs/       GuardDecision JSONL files
```

### `data/intenttracebench_v0/`

Benchmark split placeholders.

```text
splits/memory_train.jsonl
splits/validation.jsonl
splits/test.jsonl
splits/unseen_agent.jsonl
splits/unseen_domain.jsonl
```

These are for paper-quality evaluation later. Do not claim results until data and labels
exist.

## Scripts

Scripts are local entrypoints. They include a bootstrap so they work before `pip install -e`.

```text
run_mock_session.py          Runs one deterministic placeholder session
run_google_demo.py           Runs the Google demo app path
collect_openclaw_traces.py   Runs the OpenClaw trace collection placeholder
run_benchmark.py             Benchmark placeholder
replay_traces.py             Replay placeholder
index_traces.py              Retrieval indexing placeholder
run_dashboard.py             Dashboard placeholder
export_demo_report.py        Report export placeholder
```

Useful checks:

```bash
python3 scripts/run_mock_session.py
python3 scripts/run_dashboard.py
python3 scripts/collect_openclaw_traces.py
python3 -m pytest
```

## Development Ownership

| Track | Main Paths |
| --- | --- |
| Runtime + agents | `src/agentguard/runtime/`, `apps/google_adk_demo_agent/`, `apps/openclaw_trace_agents/` |
| Governance | `src/agentguard/governance/`, `data/seed_memory/` |
| Evaluation + dashboard | `src/agentguard/evaluation/`, `src/agentguard/dashboard/`, `data/scenarios/`, `data/intenttracebench_v0/` |
| PM/docs/demo | `docs/`, `README.md`, Devpost and demo materials |

## First Integration Target

The first real integration should be:

```text
data/scenarios/email_intent_drift.jsonl
    -> MockRuntimeAdapter
    -> RawTraceRecord
    -> GuardEngine
    -> GuardDecision(require_approval or block)
    -> JSONL trace output
    -> replay through rule_only, stateless_intent, full_agentguard
```

After that works, wire the same contract into Google ADK for the demo and OpenClaw for
trace collection.
