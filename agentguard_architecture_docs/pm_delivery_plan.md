# AgentGuard PM Delivery Plan

Status: current v1 delivery plan.

Last updated: 2026-05-30

## Current Build Goal

Ship a complete end-to-end AgentGuard skeleton first:

```text
trace captured -> v1 schema -> guard features -> scores -> decision -> session risk -> persisted artifacts
```

The deeper algorithms can improve after the interfaces are stable and runnable.

## Completed

- Canonical v1 schema in `src/agentguard/tracing/schema_v1.py`.
- Schema architecture and Elastic store plan in `schema_architecture.md`.
- OpenClaw productivity trace generator with controlled email/file/calendar tools.
- OpenClaw transcript reader, collector, and v1 adapter.
- Local v1 trace storage under `data/traces/v1/<namespace>/`.
- V1 firewall orchestration with features, scores, decisions, live events, and session risk.
- Placeholder scoring and decision logic that runs end to end.
- Local Google ADK demo smoke path through the v1 firewall.
- Unit tests for schema, OpenClaw parsing/adaptation/collection, CLI runner, and firewall.

## Next Milestones

1. Build real Google ADK/MCP pre-tool-call interception.
2. Implement Elastic stores from `schema_architecture.md`.
3. Convert OpenClaw traces into `IntentTraceBench v0` with `LabelRecordV1`.
4. Replace placeholder scoring with calibrated statistical and retrieval logic.
5. Connect dashboard/demo views to live events, decisions, and session risk.

## Demo Risks

| Risk | Mitigation |
| --- | --- |
| Google ADK integration takes longer than expected | Keep local `run_demo.py` path exercising the same v1 firewall. |
| OpenClaw transcripts vary by version | Keep sanitized samples and parser tests. |
| Scoring is not yet research-grade | Keep formulas explicit, deterministic, and replaceable. |
| Elastic setup consumes time | Maintain JSONL store as a local fallback with the same record shapes. |

