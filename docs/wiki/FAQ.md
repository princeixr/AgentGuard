# FAQ

## Is AgentGuard an agent framework?

No. AgentGuard is a governance layer for existing agent frameworks.

Your agent still owns:

- chat loop
- model calls
- tool selection
- tool execution
- user experience

AgentGuard owns:

- pre-execution risk evaluation
- policy enforcement
- approval requests
- audit records

## Does AgentGuard execute tools?

No. The agent executes tools only after AgentGuard allows or approval resolves.

This design keeps AgentGuard framework-neutral and easier to integrate.

## Can an LLM override deterministic policy?

No. Deterministic policy is non-overridable.

Tier 3 LLM judge produces structured evidence, but the final combiner/enforcer makes the decision.

## Do I need Redis?

For local single-process development, not always. For production or multi-replica API deployments, yes.

Redis is used for:

- live event fanout
- idempotency
- approval cache
- rate limiting

## Do I need Elastic?

No. Elastic is optional.

Use Elastic when you want richer analytics, search, or retrieval-backed governance.

## What happens if AgentGuard is down?

Recommended behavior is fail closed for risky tools.

That means the agent should avoid executing high-risk tools if it cannot get a decision.

## Can I use AgentGuard with non-Python agents?

Yes. Use the REST API.

The Python SDK is convenience, not a requirement.

## Is the dashboard public-SaaS ready?

Not yet without additional auth.

For public internet exposure, add OIDC/session auth or put it behind an identity-aware proxy.

## What license does AgentGuard use?

AgentGuard uses the Apache License, Version 2.0.

This is a permissive open-source license with an explicit patent grant, which
makes it a strong fit for infrastructure and security tooling.
