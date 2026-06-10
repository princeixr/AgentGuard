# Contributing

Thanks for helping make AgentGuard better.

## Local Checks

```bash
cd agentguard-product
PYTHONPATH=src:packages/agentguard-sdk/src ../.venv/bin/python -m pytest -q
npm --prefix apps/agentguard_dashboard test
npm --prefix apps/agentguard_dashboard run build
```

## Pull Requests

Please include:

- clear problem statement
- tests or a validation note
- docs updates for user-facing behavior
- screenshots for UI changes where possible
