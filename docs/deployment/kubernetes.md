# Kubernetes Deployment

The Helm chart lives at `agentguard-product/charts/agentguard`.

```bash
helm install agentguard agentguard-product/charts/agentguard \
  --set secrets.agentguardApiKey="$(openssl rand -hex 32)" \
  --set secrets.agentguardApiKeyPepper="$(openssl rand -hex 32)" \
  --set postgresql.password="$(openssl rand -hex 32)" \
  --set redis.password="$(openssl rand -hex 32)" \
  --set config.webOrigins=https://agentguard.example.com \
  --set ingress.enabled=false
```

The chart includes an optional single-node Postgres StatefulSet for simple installs.
It also includes optional Redis for SSE fanout, idempotency, approval cache, and API
rate limiting.
For production, prefer managed Postgres and externally managed secrets:

```bash
helm upgrade --install agentguard agentguard-product/charts/agentguard \
  --namespace agentguard --create-namespace \
  --set image.api.repository=ghcr.io/your-org/agentguard-api \
  --set image.dashboard.repository=ghcr.io/your-org/agentguard-dashboard \
  --set secrets.existingSecret=agentguard-secrets \
  --set postgresql.enabled=false \
  --set postgresql.databaseUrl='postgresql+psycopg://user:pass@host:5432/agentguard' \
  --set redis.enabled=false \
  --set redis.redisUrl='redis://:strong-password@host:6379/0' \
  --set config.webOrigins=https://agentguard.example.com
```

The API pod runs `alembic upgrade head` in an init container before serving traffic.
Configure ingress TLS and restrict API/dashboard access at the ingress layer for
internet-facing deployments.
The chart defaults `config.docsEnabled=false`; only enable API docs on private
networks or temporary staging environments.

For multi-replica API deployments, keep `config.cacheEnabled=true` and provide a
shared Redis instance. Without Redis, each API pod only has local in-memory events
and idempotency state.
