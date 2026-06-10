# AgentGuard

AgentGuard is an independent runtime security product for tool-using AI agents. It
intercepts proposed tool calls, normalizes them into security-relevant actions,
evaluates versioned policies and guard tiers, and returns an enforcement decision.

## Repository Layout

```text
apps/agentguard_dashboard/     standalone React product UI
services/agentguard_api/       deployable server boundary
src/agentguard/server/         FastAPI routes and application services
packages/agentguard-sdk/       framework-independent public client contracts
src/agentguard/firewall_v2/    policy, normalization, routing, tiers, enforcement
src/agentguard/intent/         turn-scoped intent extraction and authorization
src/agentguard/tracing/        canonical traces and live-event persistence
policies/                      versioned guard policies
benchmarks/                    pinned AgentTrust benchmark dataset
tests/                         product and integration tests
```

Agent applications live in separate repositories. The adjacent
`google-adk-personal-agent` project is the current example consumer; AgentGuard does
not import or execute it.

## Current Enforcement Flow

```text
agent tool proposal
    -> public AgentGuard SDK contract
    -> intent contract
    -> tool metadata and action normalization
    -> versioned central policy
    -> Tier 1 deterministic and AgentTrust shell checks
    -> configured higher-tier evidence
    -> deterministic decision combination
    -> allow / require approval / block
    -> trace and live event persistence
```

The SDK currently defines contracts and a fake client for integration testing. This
repository does not claim that HTTP, WebSocket, or gRPC interception is implemented.

## Setup

```bash
uv sync --extra dev
npm --prefix apps/agentguard_dashboard install
```

Copy `.env.example` to `.env` and add provider credentials only for integrations you
intend to run.

## Run

Start the API and dashboard:

```bash
make demo
```

Open:

- Dashboard: `http://127.0.0.1:5173`
- API documentation: `http://127.0.0.1:8000/api/docs`

## Verify

```bash
make test
make build-frontend
PYTHONPATH=packages/agentguard-sdk/src uv run pytest -q packages/agentguard-sdk/tests
```

Run the pinned AgentTrust benchmark:

```bash
uv run python scripts/run_agenttrust_benchmark.py
```

See:

- [repository_architecture.md](docs/repository_architecture.md) for product boundaries,
- [Guard_architecture.md](docs/Guard_architecture.md) for firewall design,
- [remote_interception_implementation_plan.md](docs/remote_interception_implementation_plan.md)
  for the separate AgentGuard and Google ADK runtime plan,
- [system_separation_audit_and_plan.md](docs/system_separation_audit_and_plan.md)
  for the file-level ownership audit and physical separation sequence.
