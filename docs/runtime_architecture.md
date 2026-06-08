# AgentGuard Runtime Architecture

Status: current implemented runtime architecture with V1 compatibility and V2 tiered
evaluation.

Last updated: 2026-06-08

## Runtime Responsibility

The runtime layer converts host-agent tool proposals into the canonical AgentGuard
schema and ensures AgentGuard has a chance to decide before consequential execution.

The canonical runtime object is `AgentGuardTraceV1`.

```text
Host runtime proposal
    -> runtime adapter
    -> AgentGuardTraceV1
    -> AgentGuardFirewallV1.intercept(trace)
    -> optional AgentGuardFirewallV2 tiered evaluation
    -> GuardDecisionV1 / combined V2 decision evidence
    -> runtime maps to allow, require_approval, or block
    -> runtime executes or returns an approval-required/blocked response
```

## Implemented Files

```text
src/agentguard/runtime/
├── runtime_adapter.py       protocol returning AgentGuardTraceV1 records
├── google_adk_adapter.py    live ADK trace session and firewall bridge
├── tool_registry.py         tool metadata, side effects, risk, and confirmation rules
├── tool_event_mapper.py     legacy helper for simple proposed/executed call mapping
├── tool_executor.py         local deterministic executor helper
└── mock_tools/              local email, file, and calendar tool fixtures
```

The older interceptor-centric runtime design has been removed from the active
architecture. Interception now happens by passing a complete `AgentGuardTraceV1` into
`AgentGuardFirewallV1`.

## Google ADK Live Runtime Path

The active Google ADK path is callback-based:

```text
Google ADK agent proposes MCP tool call
    -> apps/adk_agent before_tool_callback
    -> GoogleADKTraceSession builds AgentGuardTraceV1 using ADK/MCP tool metadata
    -> AgentGuardFirewallV1.intercept(trace)
    -> optional AgentGuardFirewallV2 evaluation
        -> Tier 1 deterministic policy
        -> Tier 2 semantic boundary if enabled and escalation is needed
        -> Tier 3 Gemini LLM judge if enabled and escalation is needed
        -> deterministic combiner
    -> optional Elastic retrieval adds similar-trace evidence
    -> trace, feature, score, decision, live events, and session risk are persisted
    -> runtime maps firewall decision to allow, require_approval, or block
    -> allow executes; require_approval and block return synthetic responses for now
    -> after_tool_callback records tool_executed or tool_failed
```

`AGENTGUARD_ADK_ENFORCE_APPROVAL=true` is the default. While the approval UI is not
implemented, `require_approval` means the tool is not executed. A `block` decision is
always enforced regardless of the approval-enforcement setting.

`AGENTGUARD_FIREWALL_MODE` controls V2 rollout:

```text
v1         V1 evaluates and enforces.
v2_shadow  V1 enforces; V2 records tier evidence.
v2         V2 combined decision is the effective runtime decision.
```

Tier execution is controlled independently:

```text
AGENTGUARD_TIER_1_ENABLED=true
AGENTGUARD_TIER_2_ENABLED=false
AGENTGUARD_TIER_3_ENABLED=false
AGENTGUARD_TIER3_ENFORCEMENT_ENABLED=false
AGENTGUARD_TIER_CONFIDENCE_THRESHOLD=0.75
AGENTGUARD_TIER3_MODEL=gemini-2.5-flash
```

Tier 3 uses Gemini through `google-genai` and requires `GOOGLE_API_KEY` when enabled.
It returns structured evidence, not direct execution authority. The deterministic
combiner preserves hard Tier 1 `block` and `require_approval` decisions.

`AGENTGUARD_MOCK_PIPELINE_ONLY=true` evaluates and logs the full runtime pipeline but
never executes the proposed ADK tool. Use this for cloud/team testing.

Set `AGENTGUARD_ELASTIC_ENABLED=true` with Elastic credentials to enable live retrieval
and Elastic mirroring for ADK runtime artifacts. `AGENTGUARD_ADK_ELASTIC_ENABLED` can
override that global setting for the ADK app only. `AGENTGUARD_ADK_FAIL_ON_ELASTIC_ERROR`
defaults to `false` so live chats can continue if Elastic writes/retrieval fail after
startup.

## OpenClaw Historical Runtime Path

OpenClaw is not a governed runtime in this repository. It is a source of historical
behavioral traces for benchmark construction.

```text
OpenClaw transcript
    -> transcript_reader.py
    -> OpenClawToolEvent
    -> OpenClawTraceV1Adapter
    -> AgentGuardTraceV1
    -> data/traces/v1/openclaw/traces.jsonl
```

The collector may also write a legacy raw-trace mirror for compatibility, but the v1
trace is the source of truth for AgentGuard development.

## Runtime Invariants

- Every governed tool proposal becomes exactly one `AgentGuardTraceV1`.
- A governed runtime must call `AgentGuardFirewallV1` before executing side-effecting tools.
- When V2 is active, tier results must be recorded as evidence and the combiner must be
  the only owner of V2 enforcement.
- Tier 3 can escalate uncertainty, but cannot weaken deterministic block or approval
  requirements.
- Runtime adapters must not leak host-framework objects into governance.
- OpenClaw collection must not add guard decisions during collection; decisions are added
  later by replay or evaluation.
- ADK tool metadata should come from the active ADK/MCP tool surface when possible and
  include category, risk level, side-effect type, confirmation requirement,
  irreversibility, and MCP server.

## Local Verification

```bash
python3 scripts/run_mock_session.py
.venv/bin/python -m pytest tests/test_google_adk_runtime.py
.venv/bin/python -m pytest
```
