# AgentGuard Product

AgentGuard is the API, firewall runtime, approval dashboard, SDK package, and deployment bundle for open-source users.

## Components

```text
src/agentguard/                 FastAPI API, firewall, tracing, storage
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

- `POST /api/v2/guard/check`
- `POST /api/v1/agents/register`
- `POST /api/v1/turns/start`
- `POST /api/v1/tool-proposals/evaluate`
- `GET /api/v1/approvals`
- `POST /api/v1/approvals/{approval_id}/approve`
- `POST /api/v1/approvals/{approval_id}/reject`
- `POST /api/v1/tool-outcomes`
- `GET /api/v1/events/stream`

Most new integrations should start with `POST /api/v2/guard/check` or the
high-level `AgentGuard.check()` SDK helper. The V1 endpoints remain available
for framework adapters and advanced custom runtimes.

## Deployment

Use Docker Compose from the repository root for local self-hosting:

```bash
cp ../.env.local.example ../.env
docker compose --env-file ../.env up --build
```

Use Helm for Kubernetes:

```bash
helm install agentguard charts/agentguard \
  --set secrets.agentguardApiKey="$(openssl rand -hex 32)" \
  --set secrets.agentguardApiKeyPepper="$(openssl rand -hex 32)" \
  --set postgresql.password="$(openssl rand -hex 32)" \
  --set redis.password="$(openssl rand -hex 32)" \
  --set config.webOrigins=https://agentguard.example.com
```
