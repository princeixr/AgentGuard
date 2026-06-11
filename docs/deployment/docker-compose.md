# Docker Compose Deployment

```bash
cp .env.local.example .env.local
docker compose --env-file .env.local up --build -d
```

Services:

- `postgres`: Postgres 16 backing production runtime records and approvals
- `redis`: Redis 7 backing distributed SSE fanout, idempotency, approval cache, and rate limits
- `agentguard-api`: FastAPI API on port `8000`
- `agentguard-dashboard`: Nginx-served React app on port `5173`

For production, do not use `.env.local.example` values. Set strong unique values
for `AGENTGUARD_API_KEY`, `AGENTGUARD_API_KEY_PEPPER`, `POSTGRES_PASSWORD`, and
`REDIS_PASSWORD`; set `AGENTGUARD_ENV=production`; set `AGENTGUARD_DOCS_ENABLED=false`;
and set `AGENTGUARD_WEB_ORIGINS` to your real HTTPS dashboard origin.

Runtime JSONL artifacts are stored in `agentguard-data`; relational runtime records,
approvals, and API keys are stored in `agentguard-postgres`; cache state is stored in
`agentguard-redis`.

On startup the API container runs:

```bash
alembic upgrade head
```

To create a DB-backed API key after startup:

```bash
docker compose exec agentguard-api agentguard-create-api-key --name "local-sdk"
```

Keep `AGENTGUARD_API_KEY` set for local dashboard bootstrapping, or use the generated
key in SDK clients.

Useful cache/rate-limit overrides:

```bash
export AGENTGUARD_RATE_LIMIT_PER_MINUTE=600
export AGENTGUARD_IDEMPOTENCY_TTL_SECONDS=1800
docker compose up --build -d
```

For Gemini-backed Tier 3/intent extraction:

```bash
export GOOGLE_API_KEY=...
export AGENTGUARD_INTENT_LLM_ENABLED=true
docker compose up --build
```

Optional Google ADK example container:

```bash
docker compose --profile adk-example up --build
```

For interactive ADK web UI development, run `google-adk-personal-agent` locally instead of via Compose.
