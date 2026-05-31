# OpenClaw Raw Artifacts

This directory stores raw OpenClaw run artifacts and sanitized parser samples.

The canonical AgentGuard output is written separately to:

```text
data/traces/v1/openclaw/traces.jsonl
```

Raw artifacts here are useful for debugging the parser and collector:

```text
data/openclaw_raw/runs/
data/openclaw_raw/transcripts/
data/openclaw_raw/normalized_events/
data/openclaw_raw/samples/
```

The first local probe showed that this OpenClaw CLI version stores session logs at:

```text
~/.openclaw/agents/<agent-id>/sessions/<session-id>.jsonl
```

The sanitized sample in `samples/openclaw_session_tool_call_sample.jsonl` preserves the
observed `toolCall` / `toolResult` schema without copying private local transcript data.

Large real transcripts should generally not be committed directly. Preserve them locally
under this directory and commit only sanitized fixtures or metadata needed for parser
tests.
