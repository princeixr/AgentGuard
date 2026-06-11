# Contributing

AgentGuard is designed to become an easy-to-adopt open-source security layer for agent developers.

## Good First Contributions

- Add tool registry metadata for more common tools.
- Improve SDK examples for popular frameworks.
- Add framework adapters.
- Add deterministic policy templates.
- Improve approval UI ergonomics.
- Add deployment guides for cloud providers.
- Add evaluation datasets and benchmarks.

## Development Loop

Backend:

```bash
cd agentguard-product
PYTHONPATH=src:packages/agentguard-sdk/src ../.venv/bin/python -m pytest -q
```

Dashboard:

```bash
npm --prefix agentguard-product/apps/agentguard_dashboard test
npm --prefix agentguard-product/apps/agentguard_dashboard run build
```

Compose:

```bash
docker compose --env-file .env.local.example config --quiet
```

## Design Principles

- Keep integrations easy.
- Prefer fail-closed behavior for high-risk actions.
- Make decisions explainable.
- Keep deterministic policy stronger than LLM recommendations.
- Avoid framework lock-in.
- Keep demo code separate from product code.
- Treat docs as part of the product.

## Contribution License

Unless explicitly stated otherwise, contributions submitted to AgentGuard are
licensed under the Apache License, Version 2.0.

By opening a pull request, you agree that your contribution may be distributed
under the project license.
