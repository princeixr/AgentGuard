# AgentGuard and Agent System Separation Audit

## Goal

Create two independently runnable and independently deployable systems before adding
network communication:

```text
AgentGuard product
  - guard API
  - policy and firewall engine
  - persistence and live events
  - AgentGuard dashboard
  - public integration contracts

Google ADK personal agent
  - ADK model and instruction
  - MCP server configuration and connections
  - tool implementations
  - agent chat service and UI
  - thin AgentGuard interceptor client
```

The agent is allowed to install an AgentGuard SDK package. It must not import
AgentGuard product internals. AgentGuard must not import the agent implementation.

## Implementation Status

Phases A-D were completed on June 9, 2026:

- `google-adk-personal-agent/` is an independent Git repository.
- Google ADK, MCP connection configuration, tool execution, and callback wiring live
  only in that repository.
- `packages/agentguard-sdk/` contains versioned framework-neutral contracts and a fake
  client used before transport exists.
- AgentGuard no longer installs Google ADK or MCP, launches an agent, exposes
  `/test-runs`, or imports an agent adapter.
- AgentGuard loads generic sanitized registration records from
  `demo/registered_agents.json`.
- Guard-side metadata inference consumes tool names, descriptions, input schemas, and
  optional AgentGuard annotations without receiving MCP credentials or connection
  details.
- The AgentGuard dashboard no longer runs the agent or assumes a fixed agent ID.

Phase E, authenticated remote registration and interception transport, is intentionally
not implemented in this change.

## Current Boundary Violations

### 1. AgentGuard server launches the Google ADK agent

Current files:

- `src/agentguard/server/services/adk_test.py`
- `src/agentguard/server/routes/agents.py`
- `src/agentguard/server/dependencies.py`
- `src/agentguard/server/app.py`

`GoogleADKTestService` imports:

- `google.adk`,
- `examples.google_adk_agent.agent`,
- the agent's model, runner, session service, and trace location.

This makes AgentGuard an agent host. It prevents independent deployment and requires
Google ADK dependencies and model credentials inside the AgentGuard server.

Required change:

- Move agent execution into the Google ADK application.
- Remove `GoogleADKTestService`.
- Remove AgentGuard `/agents/{agent_id}/test-runs`.
- Replace it later with a link or status field pointing to the independent agent UI.

### 2. AgentGuard constructs the agent definition from local agent files

Current file:

- `src/agentguard/control_plane/demo_adk_definition.py`

It owns:

- ADK agent instruction,
- model name,
- MCP configuration path,
- MCP connection status,
- available tools,
- agent test scenarios,
- Google ADK runtime configuration.

This information belongs to the agent. AgentGuard should receive a sanitized
registration manifest instead of reading agent files.

Required change:

- Move instruction, model, test scenarios, and MCP status generation to the agent.
- Replace `demo_adk_definition.py` with generic registered-agent queries.
- Store agent definitions in an AgentGuard repository through a registration contract.

### 3. MCP connection management is inside AgentGuard

Current file:

- `src/agentguard/integrations/google_adk/mcp_registry.py`

The file currently combines:

1. Agent-side responsibilities:
   - parsing MCP connection configuration,
   - resolving environment secrets,
   - checking executable availability,
   - holding stdio commands, arguments, headers, and URLs,
   - mapping prefixes,
   - registering live MCP tool objects.

2. Guard-side responsibilities:
   - inferring operation and capabilities,
   - classifying risk and reversibility,
   - mapping input-schema argument roles,
   - producing security metadata.

Required split:

```text
google-adk-agent/
  src/personal_agent/mcp/
    config.py
    registry.py
    toolsets.py

agentguard-sdk/
  integrations/google_adk/
    callbacks.py
    manifest.py

agentguard-core/
  tools/
    manifest_models.py
    metadata_inference.py
```

Agent-side registry retains secrets and connection settings. It emits only a sanitized
manifest:

```json
{
  "name": "gmail_send_email",
  "provider": "gmail",
  "transport": "mcp",
  "description": "Send an email",
  "input_schema": {},
  "annotations": {},
  "source_tool_name": "send_email"
}
```

AgentGuard never receives:

- OAuth tokens,
- MCP HTTP headers,
- local commands,
- Docker volume paths,
- credential file paths,
- full environment variables.

AgentGuard performs authoritative metadata inference from the sanitized manifest.

### 4. The Google ADK adapter contains AgentGuard product internals

Current file:

- `src/agentguard/integrations/google_adk/adapter.py`

`GoogleADKTraceSession` currently imports and owns:

- FirewallV1,
- FirewallV2,
- policy decisions,
- `IntentExtractor`,
- `TraceStore`,
- `TraceV1Builder`,
- descriptor resolution,
- local event persistence,
- session trajectory state.

This is not a thin integration adapter. It embeds most of the AgentGuard runtime inside
the agent process.

Required split:

Agent-side ADK interceptor:

- extracts ADK session, turn, and call IDs,
- captures user text,
- serializes the tool proposal,
- calls `AgentGuardClient`,
- enforces the returned verdict,
- reports execution outcome.

AgentGuard server:

- extracts intent,
- builds canonical traces,
- maintains authoritative trajectory state,
- resolves descriptors,
- normalizes actions,
- evaluates policies and tiers,
- persists decisions and events.

The replacement ADK adapter should depend only on:

- SDK request/response contracts,
- `AgentGuardClient`,
- Google ADK callback interfaces.

### 5. The agent imports AgentGuard control-plane and engine types

Current file:

- `examples/google_adk_agent/agent.py`

Current product-internal imports:

- `agentguard.control_plane.demo_adk_definition`,
- `agentguard.control_plane.registry`,
- `agentguard.firewall_v2.models.FirewallMode`,
- `GoogleADKTraceSession`,
- AgentGuard MCP registry.

Required change:

- Agent IDs and deployment IDs become agent configuration.
- Agent instruction and MCP registry become local agent modules.
- Firewall mode disappears from the agent.
- The agent imports only `agentguard_sdk` and its ADK callback helper.

Target imports should resemble:

```python
from agentguard_sdk import HttpAgentGuardClient
from agentguard_sdk.integrations.google_adk import AgentGuardAdkInterceptor
from personal_agent.config import settings
from personal_agent.mcp import build_mcp_toolsets
```

### 6. AgentGuard control plane is a seeded Google ADK registry

Current file:

- `src/agentguard/control_plane/registry.py`

It hardcodes:

- Google ADK framework,
- Google ADK agent name,
- deployment and integration IDs,
- model credential status,
- callback integration metadata.

Required change:

- Replace `DemoAgentRegistry` with a generic `AgentRegistry` interface.
- Seed demo data through fixtures or an explicit registration script.
- Agent status comes from registration and heartbeat records.
- AgentGuard must not inspect `GOOGLE_API_KEY`.

### 7. Guard Admin depends on the local ADK definition

Current file:

- `src/agentguard/server/services/guard_admin.py`

It calls `agent_definition()` to obtain tools and integration details.

Required change:

- Read the registered agent and tool manifest from `AgentRegistry`.
- Read guard configuration from AgentGuard policy and runtime services.
- Report agent connection state separately from guard component state.

### 8. AgentGuard dashboard acts as an ADK agent UI

Current files:

- `apps/agentguard_dashboard/src/features/agents/AgentDetailPage.tsx`
- `apps/agentguard_dashboard/src/api/client.ts`
- `apps/agentguard_dashboard/src/config/demo.ts`
- `apps/agentguard_dashboard/src/app/App.tsx`
- `apps/agentguard_dashboard/src/components/AppShell.tsx`

Problems:

- The Agent Detail page runs the Google ADK agent.
- The UI hardcodes a Google ADK agent ID and framework.
- Navigation defaults to a known agent.
- Copy says the dashboard launches the real agent.

Required change:

- Remove the test-agent chat panel and `runAgentTest`.
- Show the registered manifest, deployment, heartbeat, and integration status.
- Use the agent list response to select a default agent.
- Render framework and name from server data.
- Add an optional external `agent_ui_url` link.
- Keep live interception, replay, policy, memory, and operations in AgentGuard.

The independent agent UI owns chat and agent execution.

### 9. AgentGuard live state assumes Google ADK

Current files:

- `src/agentguard/server/models.py`
- `src/agentguard/server/services/agent_live.py`
- `src/agentguard/server/services/query.py`
- `src/agentguard/server/services/guard_admin.py`

Hardcoded values include:

- `google_adk_runtime`,
- `google_adk`,
- Google ADK component labels.

Required change:

- Event source comes from registered integration metadata.
- Current interception is framework-neutral.
- Health separates AgentGuard health from agent integration health.
- Guard Admin describes a generic tool interception integration.

### 10. AgentGuard package requires agent framework dependencies in development

Current `pyproject.toml` includes Google ADK and MCP in the main development extra.

Required package split:

```text
packages/
  agentguard-core/        firewall, policies, tracing, server services
  agentguard-sdk/         contracts and HTTP client
  agentguard-google-adk/  optional thin ADK callback integration

services/
  agentguard-api/

apps/
  agentguard-dashboard/

examples/ or sibling repository:
  google-adk-personal-agent/
```

The AgentGuard server installation must not install Google ADK or MCP.

## Final Ownership Matrix

| Current item | Final owner | Action |
| --- | --- | --- |
| `examples/google_adk_agent/agent.py` | Agent | Move to independent agent project |
| `examples/google_adk_agent/chat.py` | Agent | Move; later replace/add agent API |
| `config/adk_mcp_servers.toml` | Agent | Move with agent deployment |
| MCP config/parser/status classes | Agent | Move out of AgentGuard |
| MCP toolset construction | Agent | Move out of AgentGuard |
| Tool manifest serialization | SDK integration | Implement as sanitized contract |
| MCP metadata/security inference | AgentGuard core | Keep, rename, remove connection details |
| ADK callback context extraction | SDK integration | Keep as thin optional package |
| Intent extraction | AgentGuard server | Remove from agent adapter |
| Trace building | AgentGuard server | Remove from agent adapter |
| FirewallV1/V2 | AgentGuard server | Remove from agent adapter |
| Trace/event persistence | AgentGuard server | Remove from agent adapter |
| Agent registration/heartbeat | AgentGuard server | Implement generic repository |
| `GoogleADKTestService` | Agent | Delete from AgentGuard |
| `/test-runs` API | Agent | Delete from AgentGuard |
| Agent chat/test UI | Agent UI | Remove from AgentGuard dashboard |
| Policy/Guard Admin UI | AgentGuard dashboard | Keep |
| Live interception UI | AgentGuard dashboard | Keep |
| Google ADK hardcoded labels | Neither | Replace with registered metadata |
| `DemoAgentRegistry` | AgentGuard demo fixture | Replace with generic registry |

## Contracts Required Before Communication

These models should exist in a framework-neutral SDK package before HTTP is added.

### Agent registration manifest

- workspace ID,
- agent ID,
- deployment ID,
- integration ID,
- framework,
- runtime version,
- display metadata,
- system instruction hash or redacted summary,
- tool manifest version,
- sanitized tools,
- optional agent UI URL.

### Sanitized tool manifest

- canonical tool name,
- source tool name,
- provider,
- framework,
- description,
- JSON input schema,
- standardized annotations,
- transport label without credentials,
- metadata provenance.

### Turn start request

- session ID,
- turn ID,
- raw user request,
- agent/deployment/integration IDs,
- manifest version.

### Tool proposal

- call ID,
- session and turn IDs,
- intent ID,
- tool name,
- arguments,
- timestamp,
- optional prior outcome cursor.

### Enforcement response

- decision and trace IDs,
- `allow`, `require_approval`, or `block`,
- policy identity,
- explanation,
- normalized action,
- tier evidence,
- approval request ID,
- latency.

### Outcome report

- decision ID,
- call ID,
- executed, blocked, failed, or cancelled,
- redacted output summary,
- latency and error metadata.

## Physical Separation Plan

### Phase A: create independent project roots without network behavior

Create:

```text
agentguard-product/
  packages/agentguard-sdk/
  services/agentguard_api/
  apps/agentguard_dashboard/

google-adk-personal-agent/
  src/personal_agent/
  config/adk_mcp_servers.toml
  apps/personal_agent_ui/
  tests/
  pyproject.toml
```

During this phase, tests may use a fake `AgentGuardClient`, but neither project may
import files from the other project root.

Verification gate:

- AgentGuard tests run without Google ADK installed.
- Agent tests run with a fake SDK client and no AgentGuard core package installed.
- Static import scan shows no forbidden cross-project imports.

### Phase B: extract the framework-neutral SDK contracts

- Move `AgentGuardClient` into the SDK package.
- Expand it with registration, turn, proposal, and outcome methods.
- Add Pydantic request/response models.
- Add a fake test client.
- Keep transport unimplemented.

Verification gate:

- Agent callback tests use only SDK contracts.
- Contract tests validate the shared schemas independently of the server.

### Phase C: move all agent-owned code

- Move MCP registry configuration and connection management.
- Move agent instruction, model, and test scenarios.
- Move Google ADK runner and callback wiring.
- Remove Google ADK imports from AgentGuard server.
- Remove model credentials from AgentGuard runtime checks.

Verification gate:

- The agent starts independently with a fake guard client.
- AgentGuard starts independently without `.env.google_adk`.

### Phase D: make AgentGuard generic

- Replace seeded Google ADK registry with a generic repository.
- Replace local definition generation with stored manifests.
- Make Guard Admin and live state framework-neutral.
- Remove agent execution routes.
- Remove Google ADK hardcoding from the dashboard.

Verification gate:

- Register two synthetic agents with different frameworks.
- Dashboard renders both without code changes.
- AgentGuard never imports the Google ADK example.

### Phase E: add communication

Only after Phases A-D:

- implement `HttpAgentGuardClient`,
- add authenticated registration and interception routes,
- make AgentGuard authoritative for traces and decisions,
- publish SSE events directly,
- enforce fail-closed behavior.

This phase is defined in
`docs/remote_interception_implementation_plan.md`.

## Files to Remove from AgentGuard After Separation

- `src/agentguard/control_plane/demo_adk_definition.py`
- `src/agentguard/server/services/adk_test.py`
- `scripts/run_google_demo.py`
- AgentGuard-side `config/adk_mcp_servers.toml`
- the connection-management portion of
  `src/agentguard/integrations/google_adk/mcp_registry.py`
- the embedded firewall/trace implementation in
  `src/agentguard/integrations/google_adk/adapter.py`
- `/agents/{agent_id}/test-runs`
- Google ADK agent execution response models
- Google ADK-specific dashboard test panel and copy

## Files That Remain in AgentGuard

- firewall and policy engine,
- intent extraction and authorization,
- normalized action models and evaluators,
- generic trace and event schemas,
- generic control-plane models,
- server query, policy, live, replay, memory, and operations APIs,
- AgentGuard dashboard,
- AgentTrust benchmark and Tier 1 integration,
- framework-neutral SDK contracts,
- sanitized tool metadata inference.

## Definition of Complete Separation

Separation is complete before transport work begins when:

1. AgentGuard can be installed and tested without Google ADK or MCP dependencies.
2. The Google ADK agent can be installed and tested without AgentGuard core/server.
3. AgentGuard has no imports from `examples/` or an agent repository.
4. The agent has no imports from firewall, policy, tracing persistence, server, or
   control-plane modules.
5. MCP credentials and connection configuration exist only in the agent project.
6. AgentGuard dashboard cannot launch the agent.
7. AgentGuard knows an agent only through generic stored registration records.
8. Shared behavior is expressed through versioned SDK contracts, not shared files.
