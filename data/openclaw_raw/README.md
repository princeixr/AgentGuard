# OpenClaw Raw Artifacts

This directory is for raw OpenClaw run artifacts and sanitized parser samples.

The first local probe showed that this OpenClaw CLI version stores session logs at:

```text
~/.openclaw/agents/<agent-id>/sessions/<session-id>.jsonl
```

The sanitized sample in `samples/openclaw_session_tool_call_sample.jsonl` preserves the
observed `toolCall` / `toolResult` schema without copying private local transcript data.

Large real transcripts should generally not be committed directly. Preserve them locally
under `data/openclaw_raw/runs/` or `data/openclaw_raw/transcripts/` and commit only
sanitized fixtures or metadata needed for parser tests.
