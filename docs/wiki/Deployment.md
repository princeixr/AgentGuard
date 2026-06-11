# Deployment

Local:

```bash
cp .env.local.example .env.local
docker compose --env-file .env.local up --build
```

Kubernetes:

```bash
helm upgrade --install agentguard agentguard-product/charts/agentguard \
  --set secrets.agentguardApiKey="$(openssl rand -hex 32)" \
  --set secrets.agentguardApiKeyPepper="$(openssl rand -hex 32)" \
  --set postgresql.password="$(openssl rand -hex 32)" \
  --set redis.password="$(openssl rand -hex 32)" \
  --set config.webOrigins=https://agentguard.example.com
```

Production recommendations:

- Use managed Postgres.
- Use shared Redis for API replicas.
- Store API keys in a secret manager.
- Use strong Postgres and Redis passwords.
- Enable TLS at ingress.
- Set `AGENTGUARD_REQUIRE_AUTH=true`.
