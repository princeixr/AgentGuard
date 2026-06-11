# AgentGuard Helm Chart

Install locally:

```bash
helm install agentguard ./agentguard-product/charts/agentguard \
  --set secrets.agentguardApiKey="$(openssl rand -hex 32)" \
  --set secrets.agentguardApiKeyPepper="$(openssl rand -hex 32)" \
  --set postgresql.password="$(openssl rand -hex 32)" \
  --set redis.password="$(openssl rand -hex 32)" \
  --set config.webOrigins=https://agentguard.example.com
```

Use `values.yaml` to configure images, ingress, persistence, and secrets. For production,
prefer `secrets.existingSecret`, managed Postgres, and managed Redis.
