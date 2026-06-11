# Troubleshooting

## Dashboard says AgentGuard API is offline

Check containers:

```bash
docker compose ps
docker compose logs agentguard-api
```

Common causes:

- API still starting
- missing required env var
- Postgres not healthy
- Redis auth mismatch
- production validation failed

## `401 Unauthorized`

The caller’s `AGENTGUARD_API_KEY` does not match the AgentGuard product key.

Check:

```bash
grep AGENTGUARD_API_KEY agentguard-product/.env
grep AGENTGUARD_API_KEY google-adk-personal-agent/.env
```

They must match.

## Production startup fails

If `AGENTGUARD_ENV=production`, AgentGuard rejects weak configuration.

Fix:

- set `AGENTGUARD_REQUIRE_AUTH=true`
- set `AGENTGUARD_DOCS_ENABLED=false`
- use strong `AGENTGUARD_API_KEY`
- use strong `AGENTGUARD_API_KEY_PEPPER`
- use strong Postgres and Redis passwords
- set `AGENTGUARD_WEB_ORIGINS` to your HTTPS dashboard origin

## Redis authentication error

Use a password-bearing URL:

```bash
AGENTGUARD_REDIS_URL=redis://:your-password@redis:6379/0
```

For local Compose, use:

```bash
docker compose --env-file .env.local.example config --quiet
```

## Gemini / Tier 3 errors

Check:

- `GOOGLE_API_KEY` is set
- the model in `AGENTGUARD_TIER3_MODEL` exists for your API key
- network access is available
- timeout values are not too low

## Tool call runs even after rejection

This is an integration bug. The agent must enforce AgentGuard’s decision.

Review your code and ensure tool execution happens only after:

- `decision == "allow"`, or
- `decision == "require_approval"` and approval status is `approved`

## Wiki pages do not appear on GitHub

GitHub Wiki is a separate repository:

```bash
git clone https://github.com/princeixr/AgentGuard.wiki.git
cp -R docs/wiki/* AgentGuard.wiki/
cd AgentGuard.wiki
git add .
git commit -m "Update wiki"
git push
```

