# AgentGuard Development Status

Last updated: 2026-05-30

## Current Running Surface

The OpenClaw productivity environment UI is running locally:

```text
http://127.0.0.1:8765
```

Start it again with:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

The UI reads and mutates the same virtual workspace used by the OpenClaw productivity
trace agent:

```text
.openclaw-traces/productivity_workspace/
```

## Implemented Repo Areas

### Shared AgentGuard Contracts

Core Pydantic contracts are in place under:

```text
src/agentguard/core/
```

Important models currently used across the repo:

- `UserIntent`
- `ProposedToolCall`
- `ExecutedToolCall`
- `ToolOutputContext`
- `RawTraceRecord`
- `LabelRecord`
- `GuardDecision`
- `ScenarioRecord`

OpenClaw traces are normalized into `RawTraceRecord`.

### OpenClaw Trace Generation

The OpenClaw section is the most developed live path.

Implemented:

- Real OpenClaw CLI runner:
  `apps/openclaw_trace_agents/cli_runner.py`
- Transcript parser:
  `apps/openclaw_trace_agents/transcript_reader.py`
- OpenClaw event normalizer:
  `apps/openclaw_trace_agents/event_normalizer.py`
- Collection orchestrator:
  `apps/openclaw_trace_agents/trace_collector.py`
- CLI entrypoint:
  `scripts/collect_openclaw_traces.py`
- Productivity agent setup:
  `scripts/setup_openclaw_productivity_agent.py`
- Productivity environment UI:
  `scripts/run_openclaw_productivity_ui.py`
  `apps/openclaw_trace_agents/productivity_ui/`

The active OpenClaw agent is:

```text
agentguard_productivity
```

Its workspace template is:

```text
apps/openclaw_trace_agents/configs/productivity_agent/
```

It exposes deterministic virtual tools for:

- email: `gmail_search`, `gmail_read`, `gmail_draft`, `gmail_send`
- files: `file_search`, `file_read`, `file_write`, `file_delete`
- calendar: `calendar_search`, `calendar_read`, `calendar_create_event`

OpenClaw invokes these through native `exec` calls. The transcript reader maps matching
`productivity_tool.py` commands back to semantic AgentGuard tool names.

### OpenClaw Data Outputs

Raw OpenClaw artifacts:

```text
data/openclaw_raw/runs/
data/openclaw_raw/transcripts/
data/openclaw_raw/normalized_events/
```

Standardized AgentGuard raw traces:

```text
data/traces/raw/openclaw/traces.jsonl
```

Benchmark provenance wrapper:

```text
data/intenttracebench_v0/benchmark_traces.jsonl
```

Current trace processing status:

```text
OpenClaw transcript
-> parsed OpenClaw tool events
-> standardized AgentGuard RawTraceRecord
-> benchmark provenance record
```

Final benchmark processing is not complete yet. Labels, dataset manifest refresh, and
real split assignment are still pending.

### Scenarios

Existing scenario files:

```text
data/scenarios/clean_sessions.jsonl
data/scenarios/email_intent_drift.jsonl
data/scenarios/file_scope_creep.jsonl
data/scenarios/calendar_premature_action.jsonl
data/scenarios/prompt_injection.jsonl
data/scenarios/productivity_agent_scenarios.jsonl
```

`productivity_agent_scenarios.jsonl` is the current target for the consolidated OpenClaw
productivity agent.

### Google ADK Demo App

The Google ADK demo scaffold exists under:

```text
apps/google_adk_demo_agent/
```

Current files:

- `agent.py`
- `tools.py`
- `run_demo.py`
- `README.md`

This is intended to be the hackathon-facing governed runtime. It is separate from
OpenClaw trace generation. OpenClaw is only a trace source; Google ADK is the intended
demo enforcement target.

### Governance, Runtime, Evaluation, Dashboard

Framework scaffolds exist:

```text
src/agentguard/runtime/
src/agentguard/governance/
src/agentguard/evaluation/
src/agentguard/dashboard/
src/agentguard/tracing/
```

Implemented enough for contract tests and local mock/runtime flows, but not yet complete
as a production-grade governance system.

## Commands That Currently Work

Set up the OpenClaw productivity agent:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/setup_openclaw_productivity_agent.py
```

Run the OpenClaw productivity UI:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

Collect real OpenClaw productivity traces:

```bash
set -a
source .env.openclaw
set +a

AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_PRODUCTIVITY_AGENT" \
  --scenario-file data/scenarios/productivity_agent_scenarios.jsonl \
  --runs-per-scenario 1 \
  --openclaw-raw-root "$OPENCLAW_RAW_ARTIFACT_ROOT" \
  --trace-root "$AGENTGUARD_RAW_TRACE_ROOT" \
  --timeout-seconds 180
```

Run tests:

```bash
python3 -m pytest
```

Latest verified result:

```text
10 passed
```

## Remaining OpenClaw Work

High priority:

- Add state reset before each OpenClaw scenario run.
- Add trace quality validation.
- Run the full productivity scenario file cleanly.
- Expand productivity scenarios to cover more clean and unsafe workflows.
- Generate dataset manifest and real benchmark split assignments from collected traces.

Trace quality checks should verify:

- traces use semantic tool names, not raw `exec`;
- tool names match expected scenario domains;
- provenance exists for every trace;
- no guard decisions are mixed into raw trace generation;
- OpenClaw model/tool errors are surfaced clearly.

## Remaining Benchmark Work

Pending:

- Deduplicate raw traces.
- Build standardized benchmark manifest from `RawTraceRecord` + provenance.
- Create labels separately from raw traces.
- Populate memory/train/validation/test/unseen splits from real collected data.
- Add replay/evaluation scripts that compute metrics over labeled traces.

## Remaining Demo Work

Pending:

- Complete Google ADK governed runtime path.
- Route proposed Google ADK tool calls through AgentGuard before execution.
- Show guard decisions, explanations, and trace trajectory in a demo-friendly view.
- Connect benchmark traces to governance evaluation.

## Git/Workspace Notes

Generated runtime artifacts should remain uncommitted:

```text
.openclaw-traces/
data/openclaw_raw/runs/
data/openclaw_raw/transcripts/
data/openclaw_raw/normalized_events/
data/traces/raw/*/traces.jsonl
data/intenttracebench_v0/benchmark_traces.jsonl
```

Current worktree has unrelated deletions visible in `git status`, including architecture
draft paths and `MCP-Proxy`. Those were not part of the OpenClaw UI/status work and
should be reviewed before staging a commit.
