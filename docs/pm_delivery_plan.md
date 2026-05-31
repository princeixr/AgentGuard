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

- Repository scaffold for core, runtime, tracing, governance, evaluation, dashboard,
  OpenClaw trace generation, and Google ADK demo app.
- Canonical v1 schema in `src/agentguard/tracing/schema_v1.py`.
- Schema architecture document with Elastic store plan in `schema_architecture.md`.
- OpenClaw productivity agent setup with controlled email/file/calendar tools.
- OpenClaw transcript reader and trace collector.
- OpenClaw to `AgentGuardTraceV1` adapter.
- Local v1 trace storage under `data/traces/v1/<namespace>/`.
- V1 firewall orchestration with feature, score, decision, live-event, and session-risk
  persistence.
- Placeholder scoring and decision logic that runs end to end.
- Local Google ADK demo smoke path through the v1 firewall.
- Unit tests for schema, OpenClaw reader/adapter/collector, CLI runner, and firewall.

## In Progress

- Aligning docs and READMEs with the implemented v1 architecture.
- Cleaning old architecture references from the active developer-facing docs.
- Stabilizing the single OpenClaw productivity trace generator as the benchmark source.

## Next Milestones

### 1. Google ADK Live Interception

Build the real Google ADK/MCP adapter:

```text
MCP proposed tool call -> AgentGuardTraceV1 -> AgentGuardFirewallV1 -> enforce decision
```

Definition of done:

- one live demo agent tool call is intercepted before execution,
- allow/block path works,
- decision is visible in local JSONL artifacts,
- side-effecting tool is not executed after block.

### 2. Elastic Integration

Implement the stores described in `schema_architecture.md`:

- `agentguard-traces-v1`,
- `agentguard-live-events-v1`,
- `agentguard-trace-features-v1`,
- `agentguard-guard-scores-v1`,
- `agentguard-guard-decisions-v1`,
- `agentguard-session-risk-v1`,
- `agentguard-labels-v1`,
- `agentguard-scenarios-v1`.

Definition of done:

- local JSONL store can be mirrored to Elastic,
- live decisions can retrieve historical trace context,
- dashboard can read live events.

### 3. Benchmark Dataset

Convert OpenClaw productivity traces into `IntentTraceBench v0`.

Definition of done:

- traces are canonical `AgentGuardTraceV1`,
- labels are `LabelRecordV1`,
- splits exist for validation/test/unseen-agent/unseen-domain/memory-train,
- replay can compute metrics from the dataset.

### 4. Scoring Upgrade

Replace placeholder scoring with calibrated formulas:

- intent drift,
- sequence deviation,
- argument drift,
- permission risk,
- tool-output susceptibility,
- retrieval risk,
- cumulative session risk.

Definition of done:

- component scores are reproducible,
- thresholds are documented,
- benchmark metrics compare against baselines.

## Demo Risks

| Risk | Mitigation |
| --- | --- |
| Google ADK integration takes longer than expected | Keep local `run_demo.py` path exercising the same v1 firewall. |
| OpenClaw transcripts vary by version | Keep sanitized samples and parser tests. |
| Scoring is not yet research-grade | Keep formulas explicit, deterministic, and replaceable. |
| Elastic setup consumes time | Maintain JSONL store as a local fallback with the same record shapes. |

