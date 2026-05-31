# OpenClaw Trace Agents

This app group is for historical trace generation and benchmark construction.

OpenClaw agents are not governed by AgentGuard in this project. They are used to produce
real tool-use traces from a sophisticated agent. Those traces are normalized into the
canonical `AgentGuardTraceV1` schema and later used for benchmark data, Elastic memory,
and guard evaluation.

## Current Implementation

The active trace source is one controlled OpenClaw productivity agent:

```text
agentguard_productivity
```

It has access to virtual email, file, and calendar tools inside a deterministic local
workspace. This gives us cross-domain behavior from one real OpenClaw agent while keeping
the environment inspectable.

## Collection Flow

```text
Real OpenClaw productivity agent run
    -> OpenClaw session transcript
    -> transcript_reader.py
    -> OpenClawToolEvent
    -> OpenClawTraceV1Adapter
    -> AgentGuardTraceV1
    -> data/traces/v1/openclaw/traces.jsonl
```

No `GuardDecisionV1` should be generated during OpenClaw trace collection. Guard outputs
belong to later replay or benchmark evaluation.

For compatibility, the collector may also write a legacy mirror under
`data/traces/raw/openclaw/traces.jsonl`, but new development should use
`data/traces/v1/openclaw/traces.jsonl`.

## Run

Set up the real OpenClaw productivity trace agent:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/setup_openclaw_productivity_agent.py
```

Run real OpenClaw sessions after configuring model auth:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_PRODUCTIVITY_AGENT" \
  --scenario-file data/scenarios/productivity_agent_scenarios.jsonl \
  --runs-per-scenario 1 \
  --timeout-seconds 180
```

This writes:

```text
data/openclaw_raw/runs/                 raw CLI stdout/stderr and run metadata
data/openclaw_raw/transcripts/          copied OpenClaw session JSONL
data/openclaw_raw/normalized_events/    extracted OpenClawToolEvent JSONL
data/traces/v1/openclaw/traces.jsonl    canonical AgentGuardTraceV1 JSONL
data/traces/raw/openclaw/traces.jsonl   legacy compatibility mirror
data/intenttracebench_v0/benchmark_traces.jsonl
```

## Productivity Environment UI

To inspect the virtual environment used by `agentguard_productivity`:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

Open:

```text
http://127.0.0.1:8765
```

The UI shows the seeded inbox, drafts, sent messages, files, calendar events, side-effect
state, and a chat panel that can send prompts to the real OpenClaw productivity agent.

## OpenClaw Auth

OpenClaw auth setup for an isolated profile:

```bash
openclaw --profile "$OPENCLAW_TRACE_PROFILE" onboard \
  --mode local \
  --non-interactive \
  --accept-risk \
  --auth-choice openai-api-key \
  --openai-api-key "$OPENAI_API_KEY" \
  --skip-channels \
  --skip-daemon \
  --skip-skills \
  --skip-ui \
  --workspace "$PWD/$OPENCLAW_TRACE_WORKSPACE"
```

Run a quick auth check:

```bash
openclaw --profile "$OPENCLAW_TRACE_PROFILE" models status --json
```

## Implemented Modules

```text
cli_runner.py          starts real OpenClaw agent runs and captures raw artifacts
transcript_reader.py   parses OpenClaw transcript directories into tool events
trace_collector.py     orchestrates scenario -> v1 trace collection
event_normalizer.py    legacy helper for normalized event artifacts
configs/               controlled OpenClaw agent configuration templates
productivity_ui/       virtual environment browser UI
```
