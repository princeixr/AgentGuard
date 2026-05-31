# AgentGuard Shared Contract

Status: current implemented v1 contract.

Last updated: 2026-05-30

## Canonical Contract

All current development should use the v1 schema implemented in:

```text
src/agentguard/tracing/schema_v1.py
```

The design and Elastic index plan are documented in:

```text
schema_architecture.md
```

## Boundary Rule

Runtime-specific objects from Google ADK, MCP, OpenClaw, or local fixtures must be
converted into AgentGuard schema objects before they enter governance, evaluation, or
storage.

The primary boundary object is:

```text
AgentGuardTraceV1
```

## Required Record Separation

Do not mix trace facts, features, scores, decisions, labels, and session state in one
document. They are separate records because each has a different lifecycle.

```text
AgentGuardTraceV1      factual proposed tool-call record
TraceFeatureV1         derived feature record
GuardScoreV1           mathematical scoring record
GuardDecisionV1        final governance verdict
SessionRiskStateV1     cumulative session state
LiveEventV1            append-only runtime event
LabelRecordV1          human or LLM benchmark label
ScenarioRecordV1       scenario metadata
```

## Current Runtime Contract

```text
runtime adapter -> AgentGuardTraceV1 -> AgentGuardFirewallV1 -> GuardDecisionV1
```

The governed runtime must enforce `GuardDecisionV1` before side-effecting execution.

## Current Historical Trace Contract

```text
OpenClaw transcript -> OpenClawToolEvent -> AgentGuardTraceV1
```

OpenClaw traces are historical evidence for benchmark and retrieval memory. They are not
guarded during collection.

## Storage Contract

Local v1 storage currently writes:

```text
data/traces/v1/<namespace>/traces.jsonl
data/traces/v1/<namespace>/features.jsonl
data/traces/v1/<namespace>/scores.jsonl
data/traces/v1/<namespace>/decisions.jsonl
data/traces/v1/<namespace>/live_events.jsonl
data/traces/v1/<namespace>/labels.jsonl
data/traces/v1/<namespace>/session_risk/<session_id>.json
```

Elastic will mirror these stores using the index names in `schema_architecture.md`.

## Compatibility Note

Some legacy models remain in `src/agentguard/core/models.py` to keep older fixtures and
tests readable while the project migrates fully to v1. New AgentGuard work should not
build new runtime surfaces around those legacy models.

