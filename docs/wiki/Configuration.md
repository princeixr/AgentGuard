# Configuration

This page explains the most important AgentGuard environment variables.

## Product API

| Variable | Use | Production guidance |
|---|---|---|
| `AGENTGUARD_API_KEY` | Bearer token for SDK/agent calls | Generate a strong value |
| `AGENTGUARD_ENV` | `development` or `production` | Use `production` in deploy |
| `AGENTGUARD_REQUIRE_AUTH` | Require API key auth | Must be `true` |
| `AGENTGUARD_API_KEY_PEPPER` | Pepper for DB API-key hashing | Generate a strong stable value |
| `AGENTGUARD_DOCS_ENABLED` | Enable `/api/docs` | Use `false` publicly |
| `AGENTGUARD_WEB_ORIGINS` | Allowed browser origins | Use HTTPS production origin |

## Storage

| Variable | Use |
|---|---|
| `AGENTGUARD_DATABASE_URL` | Postgres SQLAlchemy URL |
| `AGENTGUARD_CACHE_ENABLED` | Enables Redis-backed runtime cache |
| `AGENTGUARD_REDIS_URL` | Redis URL with password |
| `AGENTGUARD_TRACE_ROOT` | Local trace file root |
| `AGENTGUARD_APPROVAL_ROOT` | Local approval artifact root |
| `AGENTGUARD_ELASTIC_ENABLED` | Enables Elastic integration |
| `ELASTICSEARCH_URL` | Elastic endpoint |
| `ELASTICSEARCH_API_KEY` | Elastic API key |

## Firewall

| Variable | Use |
|---|---|
| `AGENTGUARD_FIREWALL_MODE` | Keep `v2` |
| `AGENTGUARD_FORCE_BLOCK` | Emergency block-all switch |
| `AGENTGUARD_AGENTTRUST_SHELL_ENABLED` | Enables Tier 1 shell checks |
| `AGENTGUARD_INTENT_LLM_ENABLED` | Enables LLM intent extraction |
| `AGENTGUARD_INTENT_MODEL` | Gemini intent model |
| `AGENTGUARD_INTENT_TIMEOUT_SECONDS` | Intent call timeout |
| `AGENTGUARD_INTENT_CONFIDENCE_THRESHOLD` | Minimum intent confidence |
| `AGENTGUARD_TIER_CONFIDENCE_THRESHOLD` | Tier confidence threshold |
| `AGENTGUARD_TIER3_MODEL` | Gemini Tier 3 judge model |
| `AGENTGUARD_TIER3_TIMEOUT_SECONDS` | Tier 3 timeout |
| `GOOGLE_API_KEY` | Gemini API key |

## Production Startup Validation

When `AGENTGUARD_ENV=production`, AgentGuard fails startup if:

- auth is disabled
- docs are enabled
- weak/default API keys or peppers are used
- Postgres password is weak/default
- Redis is enabled without a strong password
- web origins are wildcard or localhost

This is deliberate. It prevents accidental internet exposure with local defaults.

## Secret Generation

```bash
openssl rand -hex 32
```

Use this for:

- `AGENTGUARD_API_KEY`
- `AGENTGUARD_API_KEY_PEPPER`
- Postgres password
- Redis password

