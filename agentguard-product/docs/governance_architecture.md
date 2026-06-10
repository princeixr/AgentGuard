# AgentGuard Governance Architecture

Status: current implemented v1 architecture.

Last updated: 2026-05-30

## Governance Responsibility

Governance decides whether a proposed tool call should proceed, given:

- the user intent,
- the proposed tool and arguments,
- the prior trajectory,
- context extracted from previous tool outputs,
- tool metadata and policy constraints,
- statistical and retrieval signals.

The active governance entrypoint is `AgentGuardFirewallV1`.

## Implemented Pipeline

```text
AgentGuardTraceV1
    -> TraceFeatureBuilderV1
    -> TraceFeatureV1
    -> GuardScorerV1
    -> GuardScoreV1
    -> DecisionPolicyV1
    -> GuardDecisionV1
    -> SessionRiskManagerV1
    -> SessionRiskStateV1
```

## Implemented Files

```text
src/agentguard/governance/
├── firewall_v1.py          orchestration entrypoint
├── feature_builder_v1.py   derives policy, context, retrieval, and historical features
├── scoring_v1.py           deterministic placeholder scoring formulas
├── decision_policy_v1.py   verdict thresholds and hard policy rules
├── session_risk_v1.py      cumulative session risk state
└── __init__.py             exports AgentGuardFirewallV1 and FirewallResultV1
```

## Current Logic Level

The current logic is intentionally simple and deterministic. It is built so the complete
flow can run end to end before we replace placeholder formulas with stronger methods.

Implemented now:

- hard blocks for explicitly forbidden tools,
- approval requirements for tools marked by intent or registry metadata,
- side-effect and irreversible-action risk,
- explicit constraint violation detection,
- context flags for untrusted instructions, external links, and secret-like content,
- cumulative risk state across a session,
- JSONL persistence for traces, features, scores, decisions, and live events.

Planned next:

- Elastic-backed retrieval over historical `AgentGuardTraceV1` records,
- statistical sequence rarity and argument-cluster distance,
- LLM-as-judge fallback using retrieved trace context,
- calibrated thresholds from labeled benchmark data.

## Decision Outputs

`GuardDecisionV1.decision` can be:

```text
allow
warn
review
require_approval
block
```

Each decision stores:

- final risk score,
- thresholds used,
- rules fired,
- retrieval evidence placeholder,
- optional LLM judge placeholder,
- explanation,
- latency.

## Session Risk

`SessionRiskStateV1` is updated after every scored trace. It stores cumulative component
scores, drift streaks, high-risk streaks, approval/block counters, and recent-window
entries. This is the mechanism that lets several individually subcritical tool calls
aggregate into a higher session-level risk.

## Storage

Local storage now writes under:

```text
data/traces/v1/<namespace>/traces.jsonl
data/traces/v1/<namespace>/features.jsonl
data/traces/v1/<namespace>/scores.jsonl
data/traces/v1/<namespace>/decisions.jsonl
data/traces/v1/<namespace>/live_events.jsonl
data/traces/v1/<namespace>/session_risk/<session_id>.json
```

Elastic index design is fixed in `schema_architecture.md` and will replace or mirror this
local store.
