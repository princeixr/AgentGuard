# IntentTraceBench v0

This directory stores benchmark-ready artifacts derived from canonical
`AgentGuardTraceV1` records.

Expected inputs:

- OpenClaw productivity traces from `data/traces/v1/openclaw/traces.jsonl`,
- future Google ADK live traces,
- synthetic and mock traces when needed for coverage.

Expected benchmark records:

- trace dataset JSONL,
- `LabelRecordV1` labels,
- metadata,
- train/validation/test/unseen-domain/unseen-agent splits.

The current files are early seed artifacts. The benchmark should not treat guard scores
or decisions as trace facts.

