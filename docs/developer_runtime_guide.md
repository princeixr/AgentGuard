# AgentGuard Developer Runtime Guide

Status: current implemented guide with V1 compatibility and V2 tiered evaluation.

Last updated: 2026-06-08

## Project Goal

AgentGuard is a runtime governance layer for tool-using agents. It converts each
proposed tool call into a session-aware trace, evaluates that trace before execution,
and records the resulting features, scores, decisions, and cumulative session risk.

The project has two active surfaces:

1. Google ADK demo runtime: the live governed agent path for the hackathon.
2. OpenClaw trace generation: the historical dataset path for realistic agent behavior.

Both surfaces must converge on `AgentGuardTraceV1`.

## Canonical Contract

The canonical schema lives in:

```text
src/agentguard/tracing/schema_v1.py
schema_architecture.md
```

Core records:

| Record | Purpose |
| --- | --- |
| `AgentGuardTraceV1` | One proposed tool call with intent, tool, trajectory, context, retrieval text, and execution state. |
| `LiveEventV1` | Append-only runtime timeline event. |
| `TraceFeatureV1` | Derived features for policy, context, retrieval, and historical statistics. |
| `GuardScoreV1` | Step and cumulative mathematical risk scores. |
| `GuardDecisionV1` | Final guard verdict and explanation. |
| `SessionRiskStateV1` | Upserted cumulative risk state for the session. |
| `LabelRecordV1` | Benchmark label stored separately from traces and guard outputs. |
| `ScenarioRecordV1` | Scenario metadata and expected behavior. |

## Governed Runtime Flow

```text
Host agent proposes tool call
    -> runtime adapter builds AgentGuardTraceV1
    -> AgentGuardFirewallV1.intercept(trace)
    -> optional AgentGuardFirewallV2 tiered evaluation
    -> TraceFeatureV1, GuardScoreV1, GuardDecisionV1 are persisted
    -> optional V2 tier evidence and combined decision are recorded
    -> SessionRiskStateV1 is updated
    -> runtime maps the decision to allow, require_approval, or block
    -> runtime executes or returns an approval-required/blocked response
```

No governed host agent should execute a side-effecting tool before this flow runs.

The Google ADK runtime exposes three runtime policies:

```text
allow             execute the tool
require_approval  do not execute until an approval path exists
block             never execute the tool
```

`AGENTGUARD_ADK_ENFORCE_APPROVAL=true` is the default.

V2 rollout is controlled with:

```text
AGENTGUARD_FIREWALL_MODE=v1 | v2_shadow | v2
AGENTGUARD_TIER_1_ENABLED=true
AGENTGUARD_TIER_2_ENABLED=false
AGENTGUARD_TIER_3_ENABLED=false
AGENTGUARD_TIER3_ENFORCEMENT_ENABLED=false
AGENTGUARD_MOCK_PIPELINE_ONLY=false
```

Tier 3 uses Gemini via `google-genai` and requires `GOOGLE_API_KEY` when enabled.
`AGENTGUARD_MOCK_PIPELINE_ONLY=true` is the safest mode for shared/cloud testing because
it evaluates and logs the full pipeline without executing the proposed tool.

## OpenClaw Dataset Flow

```text
Scenario JSONL
    -> real OpenClaw productivity agent
    -> OpenClaw session transcript
    -> transcript_reader.py
    -> OpenClawToolEvent
    -> OpenClawTraceV1Adapter
    -> AgentGuardTraceV1
    -> data/traces/v1/openclaw/traces.jsonl
```

OpenClaw collection is offline dataset generation. It does not call the guard during
collection. Guard outputs are produced later by replay/evaluation.

## Component Map

### `src/agentguard/tracing/`

```text
schema_v1.py                     canonical v1 models
trace_v1_builder.py              canonical trace builder
adapters/openclaw_trace_adapter.py OpenClaw event to v1 trace adapter
trace_store.py                   local JSONL/JSON persistence
serializers.py                   JSON helpers with alias support
validators.py                    legacy validation helpers
redaction.py                     redaction helpers
trace_builder.py                 legacy compatibility builder
```

### `src/agentguard/governance/`

```text
firewall_v1.py          main guard orchestration
feature_builder_v1.py   deterministic feature extraction
scoring_v1.py           placeholder mathematical scoring
decision_policy_v1.py   verdict policy and thresholds
session_risk_v1.py      cumulative session risk manager
```

### `src/agentguard/runtime/`

```text
runtime_adapter.py       runtime protocol
google_adk_adapter.py    live ADK trace session and firewall bridge
tool_registry.py         tool metadata and risk registry
tool_executor.py         deterministic local executor helper
tool_event_mapper.py     legacy compatibility mapper
mock_tools/              local email, file, and calendar tools
```

`GoogleADKTraceSession` is the active callback bridge used by `apps/adk_agent`. It
builds `AgentGuardTraceV1` records with ADK/MCP tool metadata, calls
`AgentGuardFirewallV1` before execution, optionally evaluates `AgentGuardFirewallV2`,
stores firewall artifacts, and records post-decision runtime events such as
`tool_executed`, `tool_failed`, and approval-stopped `tool_blocked`.

### `src/agentguard/firewall_v2/`

```text
engine.py                  V2 orchestration and tier escalation
config/runtime.py          environment-backed tier flags
policy/                    published policy models, loader, evaluator, store
tools/normalizers/         canonical action normalization
tiers/tier_1/              deterministic policy tier
tiers/tier_2/              semantic/retrieval boundary placeholder
tiers/tier_3/              Gemini structured LLM judge
enforcement/combiner.py    deterministic final combiner
```

Tier 3 produces structured evidence and recommendations. The combiner owns enforcement
and prevents Tier 3 from weakening deterministic block or approval outcomes.

### `apps/openclaw_trace_agents/`

```text
cli_runner.py            runs real OpenClaw CLI sessions
transcript_reader.py     extracts OpenClaw tool calls/results
trace_collector.py       orchestrates scenario collection and storage
event_normalizer.py      legacy event normalization helpers
configs/productivity_agent/ controlled OpenClaw workspace and tool fixtures
productivity_ui/         browser UI for the virtual productivity environment
```

### `apps/adk_agent/`

```text
agent.py      ADK root_agent, callbacks, shell tool, optional Gmail MCP toolset
chat.py       standalone terminal chat loop
README.md     app-specific notes
```

## Local Commands

```bash
python3 -m pytest
python3 scripts/run_mock_session.py
.venv/bin/python -m pytest tests/test_google_adk_runtime.py
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

## Development Rules

- Use `AgentGuardTraceV1` as the boundary object for all new live or historical trace work.
- Keep labels, scores, decisions, and raw trace facts in separate records.
- Use runtime tool metadata for side-effect and confirmation metadata; ADK should derive
  this from active ADK/MCP tool definitions when possible.
- Treat OpenClaw as historical trace generation, not the live governed runtime.
- Treat Google ADK as the live governed runtime target.
- Placeholder logic is acceptable only when the full component interface is implemented
  and tested end to end.
