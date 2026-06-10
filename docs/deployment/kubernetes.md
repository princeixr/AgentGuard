# Kubernetes Deployment

The Helm chart lives at `agentguard-product/charts/agentguard`.

```bash
helm install agentguard agentguard-product/charts/agentguard \
  --set secrets.agentguardApiKey=replace-me \
  --set ingress.enabled=false
```

For production, provide externally managed secrets and configure ingress TLS.

```bash
helm upgrade --install agentguard agentguard-product/charts/agentguard \
  --namespace agentguard --create-namespace \
  --set image.api.repository=ghcr.io/your-org/agentguard-api \
  --set image.dashboard.repository=ghcr.io/your-org/agentguard-dashboard \
  --set secrets.existingSecret=agentguard-secrets
```
