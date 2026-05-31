# AgentGuard Runtime Architecture

Status: current implemented v1 architecture.

Last updated: 2026-05-30

## Runtime Responsibility

The runtime layer converts host-agent tool proposals into the canonical AgentGuard
schema and ensures AgentGuard has a chance to decide before consequential execution.

The canonical runtime object is `AgentGuardTraceV1`.

```text
Host runtime proposal
    -> runtime adapter
    -> AgentGuardTraceV1
    -> AgentGuardFirewallV1.intercept(trace)
    -> GuardDecisionV1
    -> runtime executes, warns, requests approval, reviews, or blocks
```

## Implemented Files

```text
src/agentguard/runtime/
├── runtime_adapter.py       protocol returning AgentGuardTraceV1 records
├── google_adk_adapter.py    placeholder for live Google ADK/MCP interception
├── tool_registry.py         tool metadata, side effects, risk, and confirmation rules
├── tool_event_mapper.py     legacy helper for simple proposed/executed call mapping
├── tool_executor.py         local deterministic executor helper
└── mock_tools/              local email, file, and calendar tool fixtures
```

The older interceptor-centric runtime design has been removed from the active
architecture. Interception now happens by passing a complete `AgentGuardTraceV1` into
`AgentGuardFirewallV1`.

## Google ADK Live Runtime Path

The intended Google ADK path is:

```text
Google ADK agent proposes MCP tool call
    -> GoogleADKAdapter captures tool name and arguments before execution
    -> TraceV1Builder builds AgentGuardTraceV1
    -> AgentGuardFirewallV1 evaluates the trace
    -> adapter enforces GuardDecisionV1
    -> local store and future Elastic store receive events and decisions
```

The current `GoogleADKAdapter` is a placeholder that documents this contract. The local
demo in `apps/google_adk_demo_agent/run_demo.py` already exercises the same v1 firewall
with deterministic data.

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
- Runtime adapters must not leak host-framework objects into governance.
- OpenClaw collection must not add guard decisions during collection; decisions are added
  later by replay or evaluation.
- Tool metadata comes from `ToolRegistry` and should include category, side-effect type,
  confirmation requirement, irreversibility, and MCP server when known.

## Local Verification

```bash
python3 scripts/run_mock_session.py
PYTHONPATH=src python3 apps/google_adk_demo_agent/run_demo.py
python3 -m pytest
```

