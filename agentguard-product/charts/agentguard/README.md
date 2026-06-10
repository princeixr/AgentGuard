# AgentGuard Helm Chart

Install locally:

```bash
helm install agentguard ./agentguard-product/charts/agentguard \
  --set secrets.agentguardApiKey=dev-agentguard-key
```

Use `values.yaml` to configure images, ingress, persistence, and secrets.
