# AgentGuard Runtime Architecture v0.1

## Owner

**Developer 1 — Runtime + Agent Infrastructure**

Primary responsibility: build the runtime layer that runs Google ADK agent sessions, intercepts proposed tool calls before execution, converts runtime-specific events into shared AgentGuard trace models, and emits replayable raw traces.

This document inherits from `docs/shared_contract.md`.

---

## Runtime Strategy

For the hackathon, the primary runtime is:

```text
Google ADK
```

Required fallback runtime:

```text
MockRuntimeAdapter
```

OpenClaw is not an AgentGuard enforcement runtime for the current project plan. It is a
research trace source used by `apps/openclaw_trace_agents/`.

Deprecated/legacy optional runtime wording:

```text
OpenClawAdapter
```

The runtime layer must not leak Google ADK-specific objects into governance, tracing, evaluation, or dashboard modules. Everything leaving the runtime module must be converted into shared AgentGuard models.

---

## Core Runtime Goal

The runtime is not just “agent execution.”

The runtime is the **trajectory generation engine**.

Its job is to produce consistent, replayable, schema-valid traces that downstream governance and evaluation can trust.

---

## Runtime Flow

```text
Scenario
    ↓
GoogleADKAdapter.run_session()
    ↓
Google ADK Agent proposes tool call
    ↓
tool_event_mapper converts ADK tool event → ProposedToolCall
    ↓
TraceBuilder creates RawTraceRecord with prior trajectory context
    ↓
ToolInterceptor sends RawTraceRecord to GuardEngine
    ↓
GuardDecision returned
    ↓
Decision enforcement:
        allow              → execute tool
        warn               → execute tool + flag
        review             → pause / simulate no execution
        require_approval   → pause / simulate approval gate
        block              → do not execute
    ↓
ExecutedToolCall emitted
    ↓
Raw trace + execution metadata persisted
```

---

## Runtime Module Files

```text
src/agentguard/runtime/
├── runtime_adapter.py
├── google_adk_adapter.py
├── mock_runtime.py
├── interceptor.py
├── tool_event_mapper.py
├── tool_registry.py
├── tool_executor.py
└── mock_tools/
    ├── email_tools.py
    ├── file_tools.py
    └── calendar_tools.py
```

---

## Required Classes

### `RuntimeAdapter`

File:

```text
src/agentguard/runtime/runtime_adapter.py
```

```python
from typing import Protocol
from agentguard.core.models import RawTraceRecord

class RuntimeAdapter(Protocol):
    def run_session(self, scenario_id: str) -> list[RawTraceRecord]:
        """Runs one scenario and returns emitted raw traces."""
```

All runtime implementations must satisfy this interface.

---

### `GoogleADKAdapter`

File:

```text
src/agentguard/runtime/google_adk_adapter.py
```

Responsibilities:

1. Load a scenario.
2. Initialize the Google ADK agent.
3. Register tools from `ToolRegistry`.
4. Capture proposed tool calls before execution.
5. Convert ADK tool events into `ProposedToolCall`.
6. Build `RawTraceRecord`.
7. Send trace to `ToolInterceptor`.
8. Enforce `GuardDecision`.
9. Persist trace and execution metadata.
10. Return all raw traces from the session.

Skeleton:

```python
class GoogleADKAdapter:
    def __init__(
        self,
        tool_registry,
        interceptor,
        trace_builder,
        trace_store,
        max_steps: int = 6,
    ):
        ...

    def run_session(self, scenario_id: str) -> list[RawTraceRecord]:
        ...
```

---

### `MockRuntimeAdapter`

File:

```text
src/agentguard/runtime/mock_runtime.py
```

Purpose:

- deterministic fallback runtime,
- testing without Google ADK dependency,
- benchmark generation,
- CI-compatible execution.

This adapter should simulate agent tool proposals from scenario files.

Skeleton:

```python
class MockRuntimeAdapter:
    def __init__(self, interceptor, trace_builder, trace_store, max_steps: int = 6):
        ...

    def run_session(self, scenario_id: str) -> list[RawTraceRecord]:
        ...
```

The mock runtime is not a toy side project. It is a reliability mechanism. If Google ADK integration breaks during the hackathon, the evaluation and demo should still run.

---

### `ToolInterceptor`

File:

```text
src/agentguard/runtime/interceptor.py
```

Responsibilities:

- receive a `RawTraceRecord`,
- call `GuardEngine.evaluate(trace)`,
- return `GuardDecision`,
- never execute tools directly.

Skeleton:

```python
class ToolInterceptor:
    def __init__(self, guard_engine):
        self.guard_engine = guard_engine

    def intercept(self, trace: RawTraceRecord) -> GuardDecision:
        return self.guard_engine.evaluate(trace)
```

Important correction from the shared contract: the interceptor should receive the full `RawTraceRecord`, not only `ProposedToolCall`, because governance needs prior trajectory context.

---

### `ToolEventMapper`

File:

```text
src/agentguard/runtime/tool_event_mapper.py
```

Responsibilities:

- map runtime-specific tool events into shared models,
- hide Google ADK internals,
- normalize tool names, arguments, categories, and risk levels.

Required functions:

```python
def map_adk_tool_event_to_proposed_call(event, session_id: str, step_index: int) -> ProposedToolCall:
    ...

def infer_tool_category(tool_name: str) -> str:
    ...

def infer_tool_risk_level(tool_name: str) -> ToolRiskLevel:
    ...

def summarize_arguments(arguments: dict) -> str:
    ...
```

No downstream module should parse Google ADK events.

---

### `ToolRegistry`

File:

```text
src/agentguard/runtime/tool_registry.py
```

Responsibilities:

- define available tools,
- expose tool metadata,
- map tool names to callable functions,
- provide category/risk metadata.

Skeleton:

```python
class ToolRegistry:
    def register(self, tool_name: str, fn, category: str, risk_level: ToolRiskLevel):
        ...

    def get(self, tool_name: str):
        ...

    def metadata(self, tool_name: str) -> dict:
        ...
```

---

### `ToolExecutor`

File:

```text
src/agentguard/runtime/tool_executor.py
```

Responsibilities:

- execute allowed tools,
- measure latency,
- capture status,
- summarize outputs,
- return `ExecutedToolCall`.

Skeleton:

```python
class ToolExecutor:
    def execute(self, proposed_call: ProposedToolCall) -> ExecutedToolCall:
        ...
```

---

## Mock Tool Requirements

### Email Tools

File:

```text
src/agentguard/runtime/mock_tools/email_tools.py
```

Tools:

```text
gmail_search
gmail_read
gmail_draft
gmail_send
```

Required failure demo support:

1. user asks to draft, agent attempts `gmail_send`;
2. email content contains prompt injection;
3. agent reads unrelated thread.

---

### File Tools

File:

```text
src/agentguard/runtime/mock_tools/file_tools.py
```

Tools:

```text
file_search
file_read
file_summarize
file_write_summary
file_delete
```

Required failure demo support:

1. user asks to summarize one file, agent reads adjacent sensitive file;
2. tool output instructs agent to read secrets;
3. agent attempts destructive action.

---

### Calendar Tools

File:

```text
src/agentguard/runtime/mock_tools/calendar_tools.py
```

Tools:

```text
calendar_search
calendar_read
calendar_create_event
calendar_update_event
calendar_delete_event
```

Required failure demo support:

1. user asks for availability, agent creates an event;
2. agent modifies wrong meeting;
3. tool output suggests inviting an external attendee.

---

## Runtime State

The runtime should track session state explicitly.

Recommended structure:

```python
class RuntimeSessionState(BaseModel):
    session_id: str
    scenario_id: str
    user_intent: UserIntent
    prior_tool_calls: list[ExecutedToolCall] = []
    emitted_traces: list[RawTraceRecord] = []
    step_index: int = 0
    max_steps: int = 6
```

This state should not be hidden inside the model prompt. It must be explicit and inspectable.

---

## Decision Enforcement Rules

Runtime must enforce verdicts as follows:

| Verdict | Runtime Behavior |
|---|---|
| allow | Execute tool and store result |
| warn | Execute tool, store result, flag warning |
| review | Do not execute in automated mode; mark status as skipped/review |
| require_approval | Do not execute unless explicit approval simulation is enabled |
| block | Do not execute |

For hackathon demos, `review` and `require_approval` can be simulated as halted execution.

---

## Trace Emission Rules

Every proposed tool call must produce a `RawTraceRecord`.

This includes:

- allowed calls,
- blocked calls,
- failed calls,
- review/approval-gated calls.

Do not only log executed tools. The proposed-but-blocked tool call is often the most important evidence.

---

## Runtime Configuration

Recommended environment variables:

```text
AGENTGUARD_RUNTIME=google_adk
AGENTGUARD_MAX_STEPS=6
AGENTGUARD_TRACE_DIR=data/traces/raw
AGENTGUARD_USE_MOCK_TOOLS=true
AGENTGUARD_ENABLE_APPROVAL_SIMULATION=false
```

---

## Runtime Tests

Required tests:

```text
tests/test_runtime_adapter.py
tests/test_tool_event_mapper.py
tests/test_tool_executor.py
tests/test_interceptor_flow.py
```

Minimum test coverage:

1. `MockRuntimeAdapter.run_session()` returns valid `RawTraceRecord` objects.
2. Every proposed call is intercepted before execution.
3. Blocked calls are not executed.
4. `ToolEventMapper` converts tool events into `ProposedToolCall`.
5. `ToolExecutor` returns `ExecutedToolCall`.
6. `prior_tool_calls` accumulates correctly.

---

## Runtime Milestones

### Milestone R1 — Skeleton

Deliver:

- runtime module files,
- interfaces,
- mock tool functions,
- basic tests.

### Milestone R2 — Mock End-to-End

Deliver:

- one email scenario,
- proposed tool call,
- interceptor call,
- static guard verdict,
- trace emitted to JSONL.

### Milestone R3 — Google ADK Integration

Deliver:

- Google ADK agent session,
- tool call capture,
- mapping into AgentGuard schema,
- governance verdict enforcement.

### Milestone R4 — Demo-Ready Runtime

Deliver:

- three polished trajectories,
- deterministic replay,
- emitted traces compatible with dashboard/evaluation.

---

## Coding Agent Prompt for Runtime Track

```text
You are implementing the Runtime + Agent Infrastructure track for AgentGuard.

Read docs/shared_contract.md and docs/runtime_architecture.md first.

Implement only the runtime layer. Do not implement governance scoring, retrieval, dashboard, or benchmark metrics except for placeholder calls through the defined interfaces.

Tasks:
1. Create src/agentguard/runtime/runtime_adapter.py with RuntimeAdapter protocol.
2. Create GoogleADKAdapter placeholder in google_adk_adapter.py.
3. Create MockRuntimeAdapter in mock_runtime.py that can run deterministic scenario files.
4. Create ToolInterceptor that calls GuardEngine.evaluate(trace).
5. Create ToolEventMapper functions to convert runtime-specific tool events into ProposedToolCall.
6. Create ToolRegistry and ToolExecutor.
7. Implement mock email, file, and calendar tools.
8. Ensure every proposed tool call becomes a RawTraceRecord.
9. Ensure blocked/review/require_approval calls are not executed.
10. Add tests for runtime flow and schema validity.

Do not add unrelated frameworks. Do not bypass the shared Pydantic models.
```

---

## Non-Negotiables

1. No tool executes before interception.
2. No Google ADK object leaves the runtime module.
3. Every proposed call creates a raw trace.
4. Runtime must support deterministic replay through `MockRuntimeAdapter`.
5. The governance layer receives only `RawTraceRecord`.
6. The runtime must be demo-stable even if Google ADK integration is incomplete.
