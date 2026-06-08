# Current State Of Developement

Last updated: 2026-06-08

This file summarizes the AgentGuard implementation that is currently in place inside
`src/agentguard` and the connected app surfaces.

## Current Architecture

The implemented path is:

```text
runtime-specific proposed tool call
    -> AgentGuardTraceV1
    -> AgentGuardFirewallV1
    -> TraceFeatureV1
    -> GuardScoreV1
    -> GuardDecisionV1
    -> SessionRiskStateV1
    -> persisted local artifacts
```

The active rollout path also contains `AgentGuardFirewallV2`, which can run beside V1
or enforce in V2 mode:

```text
Google ADK proposed tool call
    -> AgentGuardTraceV1
    -> AgentGuardFirewallV1 compatibility path
    -> AgentGuardFirewallV2
        -> tool descriptor
        -> normalized action
        -> Tier 1 deterministic policy
        -> optional Tier 2 boundary
        -> optional Tier 3 Gemini LLM judge
        -> deterministic decision combiner
    -> runtime allow / require_approval / block
    -> persisted evidence and live events
```

The canonical schema is `AgentGuardTraceV1`, implemented in
`src/agentguard/tracing/schema_v1.py` and documented in `schema_architecture.md`.

## Running Components

### Canonical Schema

Status: running.

Implemented:

- `AgentGuardTraceV1`
- `LiveEventV1`
- `TraceFeatureV1`
- `GuardScoreV1`
- `GuardDecisionV1`
- `SessionRiskStateV1`
- `LabelRecordV1`
- `ScenarioRecordV1`

Purpose:

- one shared schema for historical OpenClaw traces and the live Google ADK traces,
- strict separation between trace facts, features, scores, decisions, labels, and session
  risk.

### Trace Storage

Status: running locally and mirrored to Elastic.

Implemented in `src/agentguard/tracing/trace_store.py`.

Current local output paths:

```text
data/traces/v1/<namespace>/traces.jsonl
data/traces/v1/<namespace>/features.jsonl
data/traces/v1/<namespace>/scores.jsonl
data/traces/v1/<namespace>/decisions.jsonl
data/traces/v1/<namespace>/live_events.jsonl
data/traces/v1/<namespace>/labels.jsonl
data/traces/v1/<namespace>/session_risk/<session_id>.json
```

Remaining:

- add semantic/vector retrieval after the lexical Elastic path is stable,
- define retention and export rules for larger benchmark runs.

### Elastic Storage

Status: running against Elastic Cloud Serverless.

Implemented under `src/agentguard/storage/`, with database workspace artifacts under
`data/elastic/`.

Current capabilities:

- environment-based Elastic config,
- index setup for all v1 stores on Elastic Cloud Serverless,
- checked-in database workspace for mappings, query bodies, notebooks, and exports,
- bulk ingestion of `AgentGuardTraceV1` from `data/traces/v1/openclaw/traces.jsonl`,
- lexical similar-trace query using domain/tool filters and retrieval text,
- Elastic retrieval provider that maps labels/decisions into `TraceFeatureV1.retrieval`,
- `AgentGuardFirewallV1` can mirror trace, feature, score, decision, live-event, and
  session-risk artifacts into Elastic,
- replay script can create decision memory from historical OpenClaw traces,
- dry-run validation without Elastic credentials.

Verified checkpoint on 2026-06-01:

```text
Elastic cluster: ecd5d17d80a44eb5b81456b138062893
OpenClaw traces ingested: 7/7
OpenClaw traces replayed through AgentGuard: 7
```

Verified Elastic indices and document counts:

```text
agentguard-traces-v1           7
agentguard-live-events-v1      21
agentguard-trace-features-v1   7
agentguard-guard-scores-v1     7
agentguard-guard-decisions-v1  7
agentguard-session-risk-v1     4
agentguard-labels-v1           0
agentguard-scenarios-v1        0
```

Commands:

```bash
python3 scripts/export_elastic_workspace.py
python3 scripts/ingest_openclaw_traces_to_elastic.py --dry-run
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/setup_elastic_indices.py
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/ingest_openclaw_traces_to_elastic.py
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/replay_traces.py --elastic --namespace openclaw_replay
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/query_elastic_traces.py --size 5
```

### Tool Registry

Status: running.

Implemented in `src/agentguard/runtime/tool_registry.py`.

It stores:

- tool category,
- risk level,
- side-effect type,
- confirmation defaults,
- irreversibility,
- MCP server,
- description.

Remaining:

- keep OpenClaw and Google ADK tool metadata aligned as both surfaces evolve,
- replace remaining rule-based fallback metadata with direct runtime/MCP metadata where
  the host framework exposes it.

### V1 Firewall

Status: running with placeholder logic.

Implemented in `src/agentguard/governance/firewall_v1.py`.

Current flow:

```text
AgentGuardTraceV1
    -> feature_builder_v1.py
    -> scoring_v1.py
    -> decision_policy_v1.py
    -> session_risk_v1.py
```

Current decisions:

```text
allow
warn
review
require_approval
block
```

Running behavior:

- persists trace, feature, score, decision, live events, and session risk,
- blocks explicitly forbidden tools,
- requires approval for sensitive tools,
- accumulates risk across the session.

Remaining:

- calibrate formulas against labeled benchmark data,
- add approval/block examples to validate decision thresholds beyond current allow-only
  replay examples.

### FirewallV2 Tiered Evaluation

Status: running for deterministic Tier 1 and Tier 3 shadow/enforcement experiments.

Implemented under `src/agentguard/firewall_v2/`.

Current flow:

```text
AgentGuardTraceV1
    -> descriptor_for_tool()
    -> normalize_tool_call()
    -> Tier1DeterministicEvaluator
    -> optional Tier2SemanticEvaluator placeholder
    -> optional Tier3LlmJudge
    -> DecisionCombinerV1
    -> FirewallV2Evaluation
```

Implemented:

- environment-backed tier flags in `config/runtime.py`,
- separate tier folders for Tier 1, Tier 2, and Tier 3,
- shared `TierResultV1` output contract,
- Tier 1 deterministic policy wrapper around the published policy evaluator,
- Tier 2 placeholder boundary that records uncertainty without pretending semantic
  retrieval is complete,
- Tier 3 Gemini judge using structured JSON output and a fixed rubric,
- auditable discovered criteria for Tier 3 with a capped weight,
- deterministic combiner that prevents Tier 3 from weakening deterministic block or
  approval decisions,
- V2 evidence persisted in `firewall_v2_evaluated` live-event payloads as
  `tier_results` and `combined_decision`,
- `AGENTGUARD_MOCK_PIPELINE_ONLY=true` mode that evaluates and logs the full pipeline
  without executing ADK tools.

Tier 3 rubric:

```text
intent alignment                  25%
tool criticality                  20%
necessity                         15%
argument scope                    15%
policy compliance                 15%
context risk                      10%
discovered criteria               audit/escalation only, capped at 20% per item
```

Current flags:

```text
AGENTGUARD_FIREWALL_MODE=v1 | v2_shadow | v2
AGENTGUARD_TIER_1_ENABLED=true
AGENTGUARD_TIER_2_ENABLED=false
AGENTGUARD_TIER_3_ENABLED=false
AGENTGUARD_TIER3_ENFORCEMENT_ENABLED=false
AGENTGUARD_TIER_CONFIDENCE_THRESHOLD=0.75
AGENTGUARD_TIER3_MODEL=gemini-2.5-flash
AGENTGUARD_MOCK_PIPELINE_ONLY=false
```

Remaining:

- implement real Tier 2 semantic/retrieval evaluation,
- add durable TierResult storage/index mappings instead of only embedding V2 tier
  evidence in live-event payloads,
- add redaction/sanitization hardening before sending broader context to Tier 3,
- calibrate confidence thresholds against labeled data,
- add model-based block policy controls if the project later allows Tier 3 hard blocks.

### OpenClaw Trace Generation

Status: running.

Implemented under `apps/openclaw_trace_agents/`.

Current flow:

```text
OpenClaw productivity agent
    -> transcript_reader.py
    -> OpenClawToolEvent
    -> OpenClawTraceV1Adapter
    -> AgentGuardTraceV1
    -> data/traces/v1/openclaw/traces.jsonl
```

Also running:

- controlled productivity workspace with email/file/calendar tools,
- browser UI for inspecting inbox, drafts, sent mail, files, calendar, and side effects,
- raw artifact capture under `data/openclaw_raw/`.

Remaining:

- grow scenario coverage,
- build final `IntentTraceBench v0` packaging step,
- label the resulting traces.

### Google ADK Runtime Path

Status: callback-level interception implemented and tested; V2 tiered evaluation can run
in shadow or enforcement mode.

Implemented:

- `apps/adk_agent/agent.py` defines a Google ADK `root_agent` with a local
  `run_shell_command` tool,
- optional Docker-backed Gmail MCP tools can be exposed through `McpToolset`,
- ADK `before_tool_callback` calls `GoogleADKTraceSession.record_tool_call()` before
  tool execution,
- `GoogleADKTraceSession` builds `AgentGuardTraceV1` records with ADK/MCP tool metadata,
- each proposed ADK tool call is sent through `AgentGuardFirewallV1`,
- each proposed ADK tool call can also be evaluated by `AgentGuardFirewallV2` when
  `AGENTGUARD_FIREWALL_MODE=v2_shadow` or `v2`, or when Tier 3 is explicitly enabled,
- ADK runtime maps firewall decisions to `allow`, `require_approval`, or `block`,
- `AGENTGUARD_ADK_ENFORCE_APPROVAL=true` stops approval-required calls by returning a
  synthetic tool response instead of executing the tool,
- ADK `after_tool_callback` and `on_tool_error_callback` record runtime events for
  `tool_executed`, `tool_failed`, and approval-stopped `tool_blocked`,
- local artifacts are written under `data/traces/v1/google_adk/` by default,
- ADK runtime can inherit global Elastic settings or override them with
  `AGENTGUARD_ADK_ELASTIC_ENABLED`,
- ADK mock-pipeline mode can evaluate and log the full guard pipeline without executing
  the proposed tool,
- `apps/adk_agent/chat.py` provides a standalone terminal chat loop.

Current tested behavior:

- direct `GoogleADKTraceSession` tests pass without importing the real ADK package,
- the session adapter builds v1 traces, calls the firewall before execution, persists
  traces/features/scores/decisions/session risk, and records post-tool runtime events,
- callback tests are present for approval blocking, approval-enforcement toggle, shell
  allow path, ADK Elastic override behavior, V2 deterministic enforcement, Tier 3
  shadow evidence, Tier 3 enforcement escalation, combiner precedence, and mock-pipeline
  non-execution behavior.

Partial or placeholder behavior:

- `GoogleADKAdapter.run_session()` still raises `NotImplementedError`; the active
  implementation is the callback/session bridge, not the `RuntimeAdapter.run_session()`
  protocol,
- runtime policy maps `allow`/`warn` to `allow`, `review`/`require_approval` to
  `require_approval`, and preserves `block` as an unconditional stop,
- there is no real approval UI yet; approval-required calls are blocked with a synthetic
  response when enforcement is enabled,
- post-tool runtime events created by `GoogleADKTraceSession._append_event()` are written
  locally, but are not yet mirrored directly to Elastic,
- Docker/Gmail MCP setup is wired and documented but not yet verified end to end with a
  real Gmail account in this environment.

Remaining:

- verify `apps/adk_agent/chat.py`, `adk run apps/adk_agent`, and `adk web` with a real
  Gemini key,
- verify Gmail MCP Docker image, OAuth volume, Gmail read/draft/send tool exposure, and
  AgentGuard blocking behavior on a test account,
- decide whether `GoogleADKAdapter.run_session()` should be implemented or removed in
  favor of the callback/session bridge,
- mirror ADK post-execution runtime events to Elastic,
- add UI/approval flow so `require_approval` can pause and resume instead of always
  returning a synthetic blocked response,
- consider exposing `warn` and `review` distinctly instead of mapping them to the
  nearest runtime enforcement action.

### Evaluation

Status: scaffold running.

Implemented under `src/agentguard/evaluation/`.

Current capabilities:

- dataset models,
- label helpers,
- metric helpers,
- replay of `AgentGuardTraceV1` through the v1 firewall,
- baseline factory pointing to the current v1 firewall.

Remaining:

- complete labeled benchmark dataset,
- implement baseline comparisons,
- generate final metrics and reports for hackathon/demo.

## Verification Commands

```bash
.venv/bin/python -m pytest
python3 scripts/run_mock_session.py
.venv/bin/python -m pytest tests/test_google_adk_runtime.py
uv run apps/adk_agent/chat.py
```

Verification note:

- `.venv/bin/python -m pytest` reports 85 passing tests in the current development
  environment.

OpenClaw UI:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

OpenClaw trace collection:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_PRODUCTIVITY_AGENT" \
  --scenario-file data/scenarios/productivity_agent_scenarios.jsonl \
  --runs-per-scenario 1 \
  --timeout-seconds 180
```

## Immediate Next Work

1. Populate `agentguard-scenarios-v1` from `data/scenarios/productivity_agent_scenarios.jsonl`.
2. Build the first label pipeline for `agentguard-labels-v1` using human labels and later
   LLM-assisted labels.
3. Verify the merged ADK callback runtime with a Gemini key and local trace output.
4. Verify Gmail MCP through Docker/OAuth on a test account and confirm AgentGuard blocks
   approval-required send actions.
5. Decide the fate of the placeholder `GoogleADKAdapter.run_session()` protocol path.
6. Mirror ADK post-tool runtime events to Elastic.
7. Expand OpenClaw scenarios to include blocked, approval-required, prompt-injection,
   cross-domain, and data-exfiltration cases.
8. Replace placeholder scoring with calibrated statistical formulas and Elastic-backed
   retrieval features.
9. Add Kibana data views/dashboard views for traces, decisions, live events, and session
   risk.
10. Promote Tier 3 from shadow to enforcement only after labeled replay shows acceptable
    false-positive and approval-load metrics.
