# AgentGuard Product

AgentGuard is the API, Firewall V2 runtime, approval dashboard, SDK package, and deployment bundle for open-source users.

## Components

```text
src/agentguard/                 FastAPI API, Firewall V2, tracing, storage
apps/agentguard_dashboard/      React dashboard and approval UI
packages/agentguard-sdk/        Lightweight Python SDK for agents
charts/agentguard/              Helm chart
Dockerfile.api                  API container
Dockerfile.dashboard            dashboard container
```

## Local Development

```bash
PYTHONPATH=src:packages/agentguard-sdk/src ../.venv/bin/python -m pytest -q
npm --prefix apps/agentguard_dashboard test
npm --prefix apps/agentguard_dashboard run build
```

## API Endpoints

- `POST /api/v1/agents/register`
- `POST /api/v1/turns/start`
- `POST /api/v1/tool-proposals/evaluate`
- `GET /api/v1/approvals`
- `POST /api/v1/approvals/{approval_id}/approve`
- `POST /api/v1/approvals/{approval_id}/reject`
- `POST /api/v1/tool-outcomes`
- `GET /api/v1/events/stream`

## Deployment

Use Docker Compose from the repository root for local self-hosting:

```bash
docker compose up --build
```

Use Helm for Kubernetes:

```bash
helm install agentguard charts/agentguard --set secrets.agentguardApiKey=replace-me
```
