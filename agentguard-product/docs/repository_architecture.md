# Repository Architecture

## Objective

AgentGuard is an independent security product. Agent applications integrate with it
through a public SDK and framework adapter. The Google ADK personal agent is an example
consumer, not a module owned by the AgentGuard server.

## Target Boundaries

```text
services/
  agentguard_api/             deployable AgentGuard server

apps/
  agentguard_dashboard/       standalone AgentGuard product UI

src/agentguard/
  server/                     stable ASGI and service entry points
  firewall_v2/                guard engine
  intent/                     turn-scoped intent contracts
  tracing/                    canonical trace and event contracts
  runtime/                    framework-neutral runtime contracts and mock tools

packages/
  agentguard-sdk/              public framework-neutral integration contracts

../google-adk-personal-agent/  independently deployed example consumer
```

## Dependency Direction

```text
independent agent
    -> AgentGuard SDK
        -> future remote transport
            -> AgentGuard server
                -> firewall, policy, tiers, tracing, storage

AgentGuard dashboard
    -> AgentGuard server API and live event stream
```

The server must never import the example-agent UI. Framework integrations may depend on
public SDK contracts but must not depend on dashboard code.

## Current Integration

The repositories are physically separated. AgentGuard stores a sanitized registration
fixture and exposes product APIs without importing Google ADK or MCP. The independent
agent uses the public SDK contracts with a fake client until remote transport is
implemented.

The `AgentGuardClient` protocol is the transport boundary. HTTP, WebSocket, and gRPC
interception are not implemented yet.
