# Configuration

## AgentGuard Product

Core variables:

- `AGENTGUARD_API_KEY`: bearer token required by SDK clients.
- `AGENTGUARD_REQUIRE_AUTH`: set `true` in production to enforce bearer/API-key auth.
- `AGENTGUARD_DOCS_ENABLED`: set `false` in production to disable `/api/docs` and OpenAPI JSON.
- `AGENTGUARD_API_KEY_PEPPER`: optional pepper used for DB API-key hashing.
- `AGENTGUARD_DATABASE_URL`: SQLAlchemy URL for Postgres, e.g. `postgresql+psycopg://...`.
- `AGENTGUARD_CACHE_ENABLED`: set `true` to enable shared cache/pub-sub behavior.
- `AGENTGUARD_REDIS_URL`: Redis URL used for distributed events, idempotency, and rate limits.
- `AGENTGUARD_RATE_LIMIT_ENABLED`: set `true` to throttle API traffic per key/IP.
- `AGENTGUARD_RATE_LIMIT_PER_MINUTE`: max API requests per minute per key/IP.
- `AGENTGUARD_IDEMPOTENCY_TTL_SECONDS`: how long repeated tool proposals return the cached decision.
- `AGENTGUARD_APPROVAL_CACHE_TTL_SECONDS`: how long approval records are mirrored in cache.
- `AGENTGUARD_WEB_ORIGINS`: comma-separated dashboard origins.
- `AGENTGUARD_TRACE_ROOT`: trace/event storage root.
- `AGENTGUARD_APPROVAL_ROOT`: approval storage root.
- `AGENTGUARD_REGISTERED_AGENTS_PATH`: registered-agent manifest path for bootstrapping.
- `AGENTGUARD_POLICY_PATH`: active policy document path.
- `GOOGLE_API_KEY`: required for Gemini-backed intent/Tier 3.

When `AGENTGUARD_ENV=production`, startup fails if auth is disabled, docs are
enabled, default/weak secrets are used, Redis is passwordless while cache is
enabled, or dashboard origins use wildcard/localhost values.

If `AGENTGUARD_DATABASE_URL` is configured, run migrations before serving traffic:

```bash
cd agentguard-product
AGENTGUARD_DATABASE_URL=postgresql+psycopg://... alembic upgrade head
```

Create DB-backed API keys with:

```bash
agentguard-create-api-key --name "production-sdk"
```

Redis is optional for a single local process, where AgentGuard falls back to an
in-memory cache. Use Redis in production or whenever more than one API replica
serves dashboard SSE streams or tool proposal traffic.

## Google ADK Agent

- `AGENTGUARD_BASE_URL`: AgentGuard API URL.
- `AGENTGUARD_API_KEY`: same key configured on AgentGuard.
- `AGENTGUARD_APPROVAL_WAIT_TIMEOUT_SECONDS`: max wait for human approval.

Framework adapter packages:

- `agentguard-sdk`: framework-neutral HTTP client and contracts.
- `agentguard-google-adk`: Google ADK callback interceptor package.
