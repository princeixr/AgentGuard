# Security

AgentGuard should be deployed as a security boundary.

Recommended controls:

- Set `AGENTGUARD_API_KEY` in a secret manager.
- Use HTTPS between agents and AgentGuard.
- Restrict `AGENTGUARD_WEB_ORIGINS`.
- Do not expose the API publicly without authentication.
- Rotate API keys periodically.
- Review what tool arguments are sent to Tier 3 LLM providers.
- Use network policies in Kubernetes.
- Keep dashboard operator access behind SSO or trusted network controls.

The SDK fails closed by default if AgentGuard is unavailable.
