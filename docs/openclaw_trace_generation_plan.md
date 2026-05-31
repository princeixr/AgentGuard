# OpenClaw Trace Generation Plan

Status: implemented baseline with real OpenClaw collection.

Last updated: 2026-05-30

## Purpose

OpenClaw is used to generate realistic historical tool-use traces for benchmark and
retrieval memory. AgentGuard is not integrated into OpenClaw as a runtime guard.

The output that matters for the rest of AgentGuard is `AgentGuardTraceV1`.

## Implemented Flow

```text
Scenario JSONL
    -> real OpenClaw productivity agent
    -> OpenClaw session transcript
    -> transcript_reader.py
    -> OpenClawToolEvent
    -> OpenClawTraceV1Adapter
    -> AgentGuardTraceV1
    -> data/traces/v1/openclaw/traces.jsonl
```

The collector also keeps raw artifacts for debugging:

```text
data/openclaw_raw/runs/
data/openclaw_raw/transcripts/
data/openclaw_raw/normalized_events/
```

A legacy raw-trace JSONL mirror may also be written under
`data/traces/raw/openclaw/traces.jsonl` for compatibility. It is not the canonical schema.

## Implemented Modules

```text
apps/openclaw_trace_agents/
├── cli_runner.py          launches real OpenClaw CLI sessions
├── transcript_reader.py   parses session JSONL tool calls and tool results
├── trace_collector.py     orchestrates scenario runs and persistence
├── event_normalizer.py    legacy normalization helper
├── configs/productivity_agent/
│   └── workspace_template/ controlled email/file/calendar environment
└── productivity_ui/       browser UI for inspecting and interacting with the environment
```

Supporting scripts:

```text
scripts/setup_openclaw_productivity_agent.py
scripts/collect_openclaw_traces.py
scripts/run_openclaw_productivity_ui.py
```

## Productivity Agent

The current single OpenClaw agent is `agentguard_productivity`. It has access to controlled
virtual tools for:

- email inbox, read, draft, send,
- file listing, reading, writing,
- calendar listing and event creation.

This lets one sophisticated OpenClaw agent generate cross-domain traces while keeping the
environment deterministic and inspectable.

## Run Commands

Set up the OpenClaw workspace:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/setup_openclaw_productivity_agent.py
```

Collect traces:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_PRODUCTIVITY_AGENT" \
  --scenario-file data/scenarios/productivity_agent_scenarios.jsonl \
  --runs-per-scenario 1 \
  --timeout-seconds 180
```

Inspect the virtual environment:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

## Remaining Work

- Expand scenarios to cover benign, drift, prompt-injection, data-scope, and side-effect
  cases.
- Add dataset build steps that package v1 traces into `data/intenttracebench_v0/`.
- Add label generation/review for `LabelRecordV1`.
- Add Elastic ingestion for historical `AgentGuardTraceV1` memory.
- Add collection quality checks for empty transcripts and missing tool results.

