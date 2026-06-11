# Security & Operations

AgentGuard is a security-sensitive runtime component. Treat it as part of your production control plane.

## Security Model

AgentGuard protects against:

- accidental tool overreach
- missing explicit user intent
- risky external side effects
- suspicious shell commands
- dangerous payment/file/email operations
- prompt-injection-influenced tool execution
- unaudited operator decisions

AgentGuard does not replace:

- application authentication
- cloud IAM
- endpoint authorization
- network segmentation
- secrets management
- secure coding of the tools themselves

## Deployment Hardening

| Area | Recommendation |
|---|---|
| API auth | Keep `AGENTGUARD_REQUIRE_AUTH=true` |
| Dashboard | Put behind private network, VPN, SSO proxy, or ingress auth |
| API docs | Disable in production |
| Postgres | Use managed Postgres with backups |
| Redis | Require password and avoid public exposure |
| TLS | Terminate TLS at ingress/load balancer |
| Secrets | Use Kubernetes Secrets, cloud secret manager, or sealed secrets |
| Images | Use signed release images and SBOMs |

## Dashboard Auth Status

The current simple deployment uses API-key based access. That is acceptable for internal demos and private deployments, but public SaaS should add OIDC/session auth before internet exposure.

Recommended future options:

- Auth0
- Clerk
- Google OAuth / generic OIDC
- Cloudflare Access
- Tailscale / private network for internal deployments

## Observability

Track:

- decision counts by `allow`, `require_approval`, `block`
- approval latency
- approval rejection rate
- blocked tool categories
- Tier 3 latency and failure rate
- AgentGuard API error rate
- Redis availability
- Postgres connection health

## Incident Response

If something looks wrong:

1. Set `AGENTGUARD_FORCE_BLOCK=true`.
2. Restart the API if needed.
3. Review approval and trace records.
4. Rotate `AGENTGUARD_API_KEY`.
5. Rotate affected downstream tool credentials.
6. Add deterministic policy for the discovered failure mode.

## Release Checklist

Before a release:

- run backend tests
- run dashboard tests/build
- run dependency audit
- verify lockfile
- build Docker images
- generate SBOMs
- sign images
- review docs
- verify production env validation

