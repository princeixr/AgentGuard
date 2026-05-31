# Current State Of Developement

Last updated: 2026-05-30

This file summarizes the AgentGuard implementation that is currently in place inside
`src/agentguard` and the connected app surfaces.

## Current Architecture

The implemented path is:

```text
runtime-specific proposed tool call
    -> AgentGuardTraceV1
    -> AgentGuardFirewallV1
    -> TraceFeatureV1
    -> GuardScoreV1
    -> GuardDecisionV1
    -> SessionRiskStateV1
    -> persisted local artifacts
```

The canonical schema is `AgentGuardTraceV1`, implemented in
`src/agentguard/tracing/schema_v1.py` and documented in `schema_architecture.md`.

## Running Components

### Canonical Schema

Status: running.

Implemented:

- `AgentGuardTraceV1`
- `LiveEventV1`
- `TraceFeatureV1`
- `GuardScoreV1`
- `GuardDecisionV1`
- `SessionRiskStateV1`
- `LabelRecordV1`
- `ScenarioRecordV1`

Purpose:

- one shared schema for historical OpenClaw traces and future live Google ADK traces,
- strict separation between trace facts, features, scores, decisions, labels, and session
  risk.

### Trace Storage

Status: running locally; initial Elastic path implemented.

Implemented in `src/agentguard/tracing/trace_store.py`.

Current local output paths:

```text
data/traces/v1/<namespace>/traces.jsonl
data/traces/v1/<namespace>/features.jsonl
data/traces/v1/<namespace>/scores.jsonl
data/traces/v1/<namespace>/decisions.jsonl
data/traces/v1/<namespace>/live_events.jsonl
data/traces/v1/<namespace>/labels.jsonl
data/traces/v1/<namespace>/session_risk/<session_id>.json
```

Remaining:

- connect Elastic retrieval results into live `TraceFeatureV1.retrieval`,
- add semantic/vector retrieval after the first lexical ingestion path is verified.

### Elastic Storage

Status: initial setup and ingestion path running.

Implemented under `src/agentguard/storage/`.

Current capabilities:

- environment-based Elastic config,
- index setup for all v1 stores,
- bulk ingestion of `AgentGuardTraceV1` from `data/traces/v1/openclaw/traces.jsonl`,
- lexical similar-trace query using domain/tool filters and retrieval text,
- dry-run validation without Elastic credentials.

Commands:

```bash
python3 scripts/ingest_openclaw_traces_to_elastic.py --dry-run
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/setup_elastic_indices.py
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/ingest_openclaw_traces_to_elastic.py
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/query_elastic_traces.py --size 5
```

### Tool Registry

Status: running.

Implemented in `src/agentguard/runtime/tool_registry.py`.

It stores:

- tool category,
- risk level,
- side-effect type,
- confirmation defaults,
- irreversibility,
- MCP server,
- description.

Remaining:

- load registry from Google ADK/MCP tool definitions automatically,
- keep OpenClaw and Google ADK tool metadata aligned.

### V1 Firewall

Status: running with placeholder logic.

Implemented in `src/agentguard/governance/firewall_v1.py`.

Current flow:

```text
AgentGuardTraceV1
    -> feature_builder_v1.py
    -> scoring_v1.py
    -> decision_policy_v1.py
    -> session_risk_v1.py
```

Current decisions:

```text
allow
warn
review
require_approval
block
```

Running behavior:

- persists trace, feature, score, decision, live events, and session risk,
- blocks explicitly forbidden tools,
- requires approval for sensitive tools,
- accumulates risk across the session.

Remaining:

- replace placeholder retrieval values with Elastic retrieval,
- calibrate formulas against labeled benchmark data,
- add LLM-as-judge fallback with retrieved evidence.

### OpenClaw Trace Generation

Status: running.

Implemented under `apps/openclaw_trace_agents/`.

Current flow:

```text
OpenClaw productivity agent
    -> transcript_reader.py
    -> OpenClawToolEvent
    -> OpenClawTraceV1Adapter
    -> AgentGuardTraceV1
    -> data/traces/v1/openclaw/traces.jsonl
```

Also running:

- controlled productivity workspace with email/file/calendar tools,
- browser UI for inspecting inbox, drafts, sent mail, files, calendar, and side effects,
- raw artifact capture under `data/openclaw_raw/`.

Remaining:

- grow scenario coverage,
- build final `IntentTraceBench v0` packaging step,
- label the resulting traces.

### Google ADK Demo Path

Status: local smoke path running; real ADK interception pending.

Implemented:

- `apps/google_adk_demo_agent/run_demo.py` creates a deterministic v1 trace,
- the trace runs through `AgentGuardFirewallV1`,
- artifacts are written under `data/traces/v1/google_adk_demo/`.

Remaining:

- implement real `GoogleADKAdapter` pre-tool-call interception,
- map MCP tool calls into `AgentGuardTraceV1`,
- enforce `GuardDecisionV1` before real tool execution,
- show decisions and live events in the demo UI.

### Evaluation

Status: scaffold running.

Implemented under `src/agentguard/evaluation/`.

Current capabilities:

- dataset models,
- label helpers,
- metric helpers,
- replay of `AgentGuardTraceV1` through the v1 firewall,
- baseline factory pointing to the current v1 firewall.

Remaining:

- complete labeled benchmark dataset,
- implement baseline comparisons,
- generate final metrics and reports for hackathon/demo.

## Verification Commands

```bash
python3 -m pytest
python3 scripts/run_mock_session.py
PYTHONPATH=src python3 apps/google_adk_demo_agent/run_demo.py
```

OpenClaw UI:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

OpenClaw trace collection:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_PRODUCTIVITY_AGENT" \
  --scenario-file data/scenarios/productivity_agent_scenarios.jsonl \
  --runs-per-scenario 1 \
  --timeout-seconds 180
```

## Immediate Next Work

1. Build the real Google ADK/MCP adapter.
2. Add Elastic storage and retrieval for the v1 records.
3. Expand OpenClaw scenarios and produce labeled `IntentTraceBench v0`.
4. Replace placeholder scoring with calibrated statistical formulas.
5. Connect dashboard views to `LiveEventV1`, `GuardDecisionV1`, and
   `SessionRiskStateV1`.
