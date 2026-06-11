# Deployment

AgentGuard supports local Docker Compose and Kubernetes via Helm.

## Local Docker Compose

```bash
cp .env.local.example .env.local
docker compose --env-file .env.local up --build -d
```

Services:

| Service | Purpose |
|---|---|
| `agentguard-api` | FastAPI API, firewall, approval runtime |
| `agentguard-dashboard` | React approval/dashboard UI served by Nginx |
| `postgres` | Runtime records, approvals, API keys |
| `redis` | SSE fanout, cache, rate limits, idempotency |
| `google-adk-agent` | Optional example agent profile |

Optional ADK example:

```bash
docker compose --env-file .env.local --profile adk-example up --build
```

## Kubernetes with Helm

```bash
helm upgrade --install agentguard agentguard-product/charts/agentguard \
  --namespace agentguard --create-namespace \
  --set secrets.agentguardApiKey="$(openssl rand -hex 32)" \
  --set secrets.agentguardApiKeyPepper="$(openssl rand -hex 32)" \
  --set postgresql.password="$(openssl rand -hex 32)" \
  --set redis.password="$(openssl rand -hex 32)" \
  --set config.webOrigins=https://agentguard.example.com
```

## Production Recommendation

For real production, prefer managed services:

```bash
helm upgrade --install agentguard agentguard-product/charts/agentguard \
  --namespace agentguard --create-namespace \
  --set image.api.repository=ghcr.io/your-org/agentguard-api \
  --set image.dashboard.repository=ghcr.io/your-org/agentguard-dashboard \
  --set secrets.existingSecret=agentguard-secrets \
  --set postgresql.enabled=false \
  --set postgresql.databaseUrl='postgresql+psycopg://user:strong-password@host:5432/agentguard' \
  --set redis.enabled=false \
  --set redis.redisUrl='redis://:strong-password@host:6379/0' \
  --set config.webOrigins=https://agentguard.example.com
```

## Production Checklist

- Use `AGENTGUARD_ENV=production`.
- Set `AGENTGUARD_REQUIRE_AUTH=true`.
- Set `AGENTGUARD_DOCS_ENABLED=false`.
- Use strong API keys and peppers.
- Use password-protected Redis.
- Use managed Postgres when possible.
- Put API and dashboard behind TLS.
- Restrict dashboard access at the network/ingress layer if you do not yet have user login.
- Run database migrations before serving traffic.
- Keep real `.env` files out of Git.

## Scaling Notes

| Component | Scaling guidance |
|---|---|
| API | Can run multiple replicas when Redis and Postgres are shared |
| Dashboard | Stateless; scale behind normal HTTP load balancer |
| Redis | Required for multi-replica live events and idempotency |
| Postgres | Source of truth for runtime records and approvals |
| Elastic | Optional for analytics/retrieval-backed decisions |

