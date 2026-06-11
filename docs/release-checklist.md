# Release Checklist

Use this checklist before publishing a public AgentGuard release.

## Required Checks

- Run backend tests: `PYTHONPATH=src:packages/agentguard-sdk/src pytest -q`
- Run dashboard tests and build: `npm --prefix agentguard-product/apps/agentguard_dashboard test && npm --prefix agentguard-product/apps/agentguard_dashboard run build`
- Verify dependency lock: `UV_CACHE_DIR=.uv-cache uv lock --project agentguard-product --check`
- Audit Python dependencies: `python -m pip_audit`
- Audit dashboard dependencies: `npm --prefix agentguard-product/apps/agentguard_dashboard audit --audit-level=high`
- Validate Compose config: `docker compose --env-file .env.local.example config --quiet`
- Validate Helm chart with real secrets set.

## Supply Chain

- Build API and dashboard Docker images from the locked dependency export.
- Generate SBOMs for both images and attach them to the CI/release artifacts.
- Sign pushed images with Cosign using GitHub OIDC.
- Review direct Git dependencies before release; `agent-trust` is pinned to a commit but is not PyPI-auditable.

## Production Config

- Set `AGENTGUARD_ENV=production`.
- Set `AGENTGUARD_REQUIRE_AUTH=true`.
- Set `AGENTGUARD_DOCS_ENABLED=false`.
- Use strong unique `AGENTGUARD_API_KEY`, `AGENTGUARD_API_KEY_PEPPER`, `POSTGRES_PASSWORD`, and `REDIS_PASSWORD`.
- Set `AGENTGUARD_WEB_ORIGINS` to the real HTTPS dashboard origin.
- Prefer managed Postgres and managed Redis for public deployments.

## Documentation Review

- Confirm quickstart commands still work.
- Confirm SDK examples do not include production-looking default secrets.
- Confirm Kubernetes docs require explicit secrets.
- Update screenshots/GIFs if approval UI or runtime flow changed.
