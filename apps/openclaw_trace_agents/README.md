# OpenClaw Trace Agents

This app group is for research trace generation and benchmark construction.

OpenClaw agents are not governed by AgentGuard in this project. They are used to produce
real tool-use traces from sophisticated agents. Those traces are normalized into the
AgentGuard raw trace schema and later used to build the benchmark dataset.

## Current Implementation

The current Python implementation includes deterministic OpenClaw-style event producers
for email, file, and calendar domains. These are test fixtures for the collector pipeline,
not the final research trace source.

The real implementation target is:

```text
Real OpenClaw agent run
    -> transcript.jsonl or Gateway/App-SDK event stream
    -> transcript_reader.py or cli_runner.py
    -> event_normalizer.py
    -> RawTraceRecord
    -> data/traces/raw/openclaw/
```

No `GuardDecision` should be generated during OpenClaw trace collection. Guard outputs
belong to later benchmark evaluation.

## Run

From the repository root:

```bash
python3 scripts/collect_openclaw_traces.py
```

Useful options:

```bash
python3 scripts/collect_openclaw_traces.py --scenario-file data/scenarios/email_intent_drift.jsonl
python3 scripts/collect_openclaw_traces.py --trace-root /tmp/agentguard-traces
```

The default mode uses deterministic fixtures for local validation. To run real OpenClaw
sessions after configuring model auth:

```bash
python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_DEFAULT_AGENT" \
  --scenario-file data/scenarios/email_intent_drift.jsonl \
  --runs-per-scenario 1 \
  --timeout-seconds 180
```

This writes:

```text
data/openclaw_raw/runs/                 raw CLI stdout/stderr and run metadata
data/openclaw_raw/transcripts/          copied OpenClaw session JSONL
data/openclaw_raw/normalized_events/    extracted OpenClawToolEvent JSONL
data/traces/raw/openclaw/traces.jsonl   AgentGuard RawTraceRecord JSONL
data/intenttracebench_v0/benchmark_traces.jsonl
```

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

## Planned Real OpenClaw Modules

```text
cli_runner.py          starts real OpenClaw agent runs and captures raw artifacts
transcript_reader.py   parses OpenClaw transcript directories into tool events
event_normalizer.py    converts tool events into AgentGuard RawTraceRecord objects
trace_collector.py     orchestrates scenario -> trace collection
configs/               three controlled OpenClaw agent configurations
```
