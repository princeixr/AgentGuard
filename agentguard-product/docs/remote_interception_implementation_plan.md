# Remote Interception Implementation Plan

## Objective

Run AgentGuard and the Google ADK personal agent as independent applications:

```text
Google ADK agent process
    -> AgentGuard SDK HTTP client
        -> AgentGuard server
            -> intent extraction
            -> normalization
            -> policy and tier evaluation
            -> authoritative decision persistence
            -> live dashboard events
    <- allow / require_approval / block
Google ADK callback enforces the returned verdict
```

The agent must not import the firewall engine, policy loader, trace store, or dashboard
code. AgentGuard must not import or launch the Google ADK example.

## Current State

The repository has clean package boundaries, but runtime behavior is still in-process:

- `GoogleADKTraceSession` builds traces and extracts intent inside the agent process.
- `InProcessAgentGuardClient` calls `AgentGuardFirewallV2` directly.
- The agent writes traces and live events directly to `data/traces`.
- The dashboard server discovers those events by polling the same filesystem.
- Agent test routes can import and launch the checked-in Google ADK example.
- Approval decisions stop execution, but live approval and resume are not implemented.

This works for a local combined demo but is not an external AgentGuard deployment.

## Required Runtime Applications

### 1. AgentGuard server

Owns:

- registered agents and tool manifests,
- turn-scoped intent contracts,
- trace construction and trajectory state,
- tool normalization,
- policy loading and versioning,
- tier routing and evaluation,
- final enforcement decisions,
- approvals,
- trace, decision, and outcome persistence,
- live-event publication,
- dashboard APIs.

It runs independently, for example on `127.0.0.1:8000`.

### 2. AgentGuard dashboard

Reads only AgentGuard server APIs and SSE streams.

It must never read the agent process or a shared trace directory directly.

It runs independently, for example on `127.0.0.1:5173`.

### 3. Google ADK agent service

Owns:

- the ADK model and agent instruction,
- registered terminal and MCP tools,
- the ADK chat session,
- framework callbacks,
- actual tool execution.

It must use the public AgentGuard SDK and must not instantiate FirewallV2.

It runs independently, for example on `127.0.0.1:8100`.

### 4. Personal-agent UI

Calls the Google ADK agent service, not AgentGuard.

It displays the conversation and tool execution results. Guard decisions remain visible
in the separate AgentGuard dashboard.

## Protocol

Use synchronous HTTP for enforcement. A tool callback cannot safely continue until it
has a verdict, so WebSocket is not required for the initial decision path.

Use SSE from AgentGuard to the dashboard for live observation.

### Agent registration

```http
PUT /api/v1/integrations/agents/{agent_id}
```

Supplies:

- workspace and deployment identity,
- framework and runtime version,
- system instruction hash,
- tool manifest,
- tool schemas and metadata,
- integration credential.

### Turn start

```http
POST /api/v1/interceptions/turns
```

Supplies:

- agent, deployment, session, and turn IDs,
- raw user request,
- available tool manifest version.

AgentGuard extracts and persists one intent contract and returns its `intent_id`.

### Tool proposal

```http
POST /api/v1/interceptions/evaluate
```

Supplies:

- session, turn, intent, and call IDs,
- tool name and arguments,
- prior tool outcomes or trajectory cursor,
- runtime metadata.

AgentGuard:

1. validates integration identity,
2. resolves tool metadata,
3. builds the canonical trace,
4. normalizes the action,
5. evaluates policy and required tiers,
6. persists evidence,
7. publishes live events,
8. returns an authoritative verdict.

Response fields:

- decision ID,
- trace ID,
- verdict: `allow`, `require_approval`, or `block`,
- explanation,
- matched policy rules,
- normalized action,
- tier evidence,
- policy ID, version, and hash,
- optional approval request ID,
- evaluation latency.

### Tool outcome

```http
POST /api/v1/interceptions/{decision_id}/outcome
```

The agent reports:

- executed, blocked, failed, or cancelled,
- redacted output summary,
- latency,
- error information.

AgentGuard completes the trace and emits the final live event.

### Approval

For the first working remote flow, `require_approval` is fail-closed and does not
execute. The dashboard can approve or reject the request, but the agent must poll or
wait for the approval result before executing.

Later versions may add WebSocket delivery for approval resume. This is separate from
the synchronous evaluation protocol.

## Failure Semantics

Security behavior must be explicit:

- connection timeout: block or require approval,
- invalid response schema: block,
- AgentGuard 5xx: block,
- unknown agent or integration: block,
- unknown tool with side effects: require approval or block,
- duplicate call ID: return the original idempotent decision,
- outcome retry: idempotent,
- configured read-only fail-open mode: optional and disabled by default.

Recommended initial timeout: two seconds for Tier 1-only decisions. Tier 3 routes need
a separately configured larger budget.

## SDK Changes

Add:

- `HttpAgentGuardClient`,
- versioned request and response models,
- retry and timeout configuration,
- integration-key authentication,
- idempotency headers,
- explicit fail-closed behavior,
- `start_turn`, `evaluate`, and `report_outcome` methods.

Keep `InProcessAgentGuardClient` only for unit tests and embedded development.

## ADK Integration Changes

Refactor the callback adapter so it:

- does not instantiate FirewallV1 or FirewallV2,
- does not load policies,
- does not write AgentGuard traces,
- starts one remote intent turn per user request,
- sends every proposed tool call to AgentGuard,
- executes only `allow`,
- pauses or stops on `require_approval`,
- returns a blocked tool response on `block`,
- reports the actual outcome after execution.

The adapter may maintain a small local trajectory cache, but AgentGuard remains the
authoritative session state.

## Server Changes

Add:

- interception request models,
- integration authentication,
- an interception application service,
- an authoritative session/turn store,
- evaluation and outcome routes,
- decision idempotency,
- event publication at request time rather than filesystem polling,
- persisted approval records.

The existing query APIs and dashboard models can remain, but live events should be
published directly when the server records them.

## UI Changes

### AgentGuard dashboard

Display:

- agent connection and heartbeat,
- registered tool manifest,
- live proposal, normalization, policy and tier stages,
- final authoritative decision,
- evaluation latency,
- approval state,
- reported execution outcome.

Remove demo language that implies shared-process execution.

### Google ADK agent UI

Create a separate minimal chat UI with:

- user prompt input,
- assistant messages,
- proposed tool calls,
- AgentGuard verdict summaries,
- tool outputs,
- connection status for both ADK and AgentGuard.

## Configuration

AgentGuard server:

```env
AGENTGUARD_SERVER_HOST=127.0.0.1
AGENTGUARD_SERVER_PORT=8000
AGENTGUARD_FIREWALL_MODE=v2
AGENTGUARD_INTEGRATION_KEYS=demo-google-adk:replace-me
AGENTGUARD_FAIL_CLOSED=true
```

Google ADK agent:

```env
GOOGLE_API_KEY=...
AGENTGUARD_BASE_URL=http://127.0.0.1:8000
AGENTGUARD_INTEGRATION_ID=demo-google-adk
AGENTGUARD_INTEGRATION_KEY=replace-me
AGENTGUARD_REQUEST_TIMEOUT_SECONDS=2
```

## Development Phases

### Phase 1: remote Tier 1 enforcement

- Add versioned interception contracts.
- Add server evaluation and outcome endpoints.
- Implement `HttpAgentGuardClient`.
- Refactor ADK callbacks to use the remote client.
- Persist and stream decisions from the server.
- Keep approval fail-closed.

Verification:

- a safe read-only command is allowed and executed,
- `rm -rf` is blocked before execution,
- AgentTrust shell evidence appears in the dashboard,
- stopping AgentGuard causes the agent to fail closed,
- repeated call IDs return the same decision.

### Phase 2: independent agent service and UI

- Add an ADK chat API.
- Add a separate personal-agent UI.
- Remove server imports of the example agent.
- Run four processes independently: guard API, guard UI, agent API, agent UI.

Verification:

- chat works while the dashboard independently observes the same trace,
- stopping the dashboard does not stop enforcement,
- stopping AgentGuard prevents side-effecting tool execution.

### Phase 3: approval lifecycle

- Persist pending approvals.
- Allow Guard Admin to approve or reject.
- Add agent polling or long-poll wait.
- Execute only after a valid approval token.

Verification:

- approval-required email or filesystem write pauses,
- reject prevents execution,
- approve executes exactly once,
- expired or replayed approval tokens are rejected.

### Phase 4: production hardening

- durable database and event bus,
- TLS and proper service authentication,
- multi-tenant workspace isolation,
- rate limiting,
- audit retention and redaction,
- deployment packaging,
- metrics and tracing,
- horizontal scaling.

## Immediate Definition of Done

The first complete two-process enforcement milestone is achieved when:

1. AgentGuard runs without importing Google ADK.
2. The Google ADK agent runs without importing the firewall engine.
3. Every tool proposal requires a server verdict.
4. A block response prevents actual tool execution.
5. AgentGuard alone persists traces, decisions, and outcomes.
6. The dashboard receives the decision live from AgentGuard.
7. Loss of AgentGuard connectivity fails closed.
