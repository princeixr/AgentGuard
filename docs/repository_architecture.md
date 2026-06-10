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

examples/
  google_adk_agent/           independent demo agent
    ui/                       independent personal-agent UI boundary

src/agentguard/
  server/                     stable ASGI and service entry points
  sdk/                        framework-independent client contract
  integrations/google_adk/    public Google ADK integration
  firewall_v2/                guard engine
  intent/                     turn-scoped intent contracts
  tracing/                    canonical trace and event contracts
  runtime/                    framework-neutral runtime contracts and mock tools
```

## Dependency Direction

```text
example agent
    -> AgentGuard Google ADK integration
        -> AgentGuard SDK
            -> remote AgentGuard server
                -> firewall, policy, tiers, tracing, storage

AgentGuard dashboard
    -> AgentGuard server API and live event stream
```

The server must never import the example-agent UI. Framework integrations may depend on
public SDK contracts but must not depend on dashboard code.

## Current Local Integration

The current server still exposes demo-only routes that can launch the checked-in Google
ADK example. This supports local product testing while interception still uses
`InProcessAgentGuardClient`. No remote transport has been introduced.

The next phase will add versioned remote interception contracts and an HTTP client
behind `AgentGuardClient`.
