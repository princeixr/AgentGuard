# OpenClaw Trace Generation Plan

OpenClaw is a trace source for benchmark construction. It is not an AgentGuard runtime
enforcement target.

## Objective

Generate real-life agent tool-use traces from three real OpenClaw agents, then normalize
those traces into the AgentGuard `RawTraceRecord` schema. The resulting dataset becomes
the basis for labels, retrieval memory, baseline comparisons, and AgentGuard development.

## Target Pipeline

```text
Scenario JSONL
    -> OpenClaw agent config
    -> real OpenClaw run
    -> raw OpenClaw transcript or event stream
    -> OpenClawTranscriptReader / OpenClawCliRunner
    -> OpenClawEventNormalizer
    -> RawTraceRecord JSONL
    -> labels and benchmark splits
    -> AgentGuard evaluation
    -> Google ADK demo validation
```

## Three Agent Configurations

### Email Agent

Purpose: email-oriented tool-use traces.

Tool surface:

- email search
- email read
- email draft
- email send against mock/sandbox destination

Target failures:

- draft vs send
- wrong recipient
- prompt injection from email body
- reading unrelated private thread

### File Agent

Purpose: file/document workflow traces.

Tool surface:

- file search
- file read
- file summarize
- file write summary
- destructive operations only inside sandbox

Target failures:

- scope creep into adjacent private files
- argument drift to wrong file
- premature write/delete
- prompt injection from file contents

### Calendar Agent

Purpose: calendar/workflow traces.

Tool surface:

- calendar search
- calendar read
- calendar create
- calendar update
- calendar delete only inside sandbox/mock calendar

Target failures:

- availability check becomes event creation
- wrong event update
- external attendee injection
- premature irreversible workflow action

## Repository Areas

```text
apps/openclaw_trace_agents/
    configs/              planned real OpenClaw configs
    cli_runner.py         runs OpenClaw and captures raw artifacts
    transcript_reader.py  parses transcript.jsonl into OpenClawToolEvent
    event_normalizer.py   converts events to RawTraceRecord
    trace_collector.py    orchestrates collection
    *_agent.py            temporary deterministic fixtures

data/openclaw_raw/
    runs/                 original CLI stdout/stderr and metadata
    transcripts/          copied raw OpenClaw transcript dirs
    normalized_events/    intermediate normalized OpenClaw events

data/traces/raw/openclaw/
    traces.jsonl          AgentGuard RawTraceRecord output
```

## Development Phases

### Phase 1: Collector Contract

Status: scaffolded.

Deliverables:

- deterministic collector fixtures,
- `OpenClawEventNormalizer`,
- `OpenClawTraceCollector`,
- JSONL output to `data/traces/raw/openclaw/`,
- tests proving collection emits raw traces only.

### Phase 2: Real Transcript Ingestion

Deliverables:

- obtain one real OpenClaw transcript directory,
- implement `OpenClawTranscriptReader.read_tool_events`,
- map transcript tool-call entries into `OpenClawToolEvent`,
- preserve source transcript under `data/openclaw_raw/transcripts/`,
- produce `RawTraceRecord` output without guard decisions.

Exit criteria:

```text
One real OpenClaw session produces at least one valid RawTraceRecord.
```

### Phase 3: CLI Scenario Runner

Deliverables:

- implement `OpenClawCliRunner`,
- run one scenario against one selected OpenClaw agent,
- capture stdout/stderr/run metadata,
- locate transcript directory,
- normalize transcript into traces.

Exit criteria:

```text
python3 scripts/collect_openclaw_traces.py --agent email --scenario-file ...
```

runs a real OpenClaw agent and writes raw traces.

Current command shape:

```bash
python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_DEFAULT_AGENT" \
  --scenario-file data/scenarios/email_intent_drift.jsonl \
  --runs-per-scenario 1
```

### Phase 4: Three Real Agent Configs

Deliverables:

- email OpenClaw config,
- file OpenClaw config,
- calendar OpenClaw config,
- sandbox/mock side effects,
- documented setup steps.

Exit criteria:

```text
Each agent can run at least five scenarios and produce schema-valid traces.
```

### Phase 5: Dataset Build

Deliverables:

- 50-75 sessions,
- 300-500 tool-call traces,
- raw OpenClaw artifacts preserved,
- normalized traces in `data/traces/raw/openclaw/`,
- labels in `data/traces/labeled/`,
- benchmark split files in `data/intenttracebench_v0/splits/`.

## Non-Negotiables

1. Do not run AgentGuard governance during OpenClaw collection.
2. Preserve raw OpenClaw artifacts for auditability.
3. Normalize all traces into `RawTraceRecord`.
4. Keep side effects sandboxed or mocked.
5. Store labels and guard outputs only after raw trace collection.
6. Do not claim benchmark results until labels and metrics are computed.
