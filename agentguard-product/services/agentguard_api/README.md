# AgentGuard API Service

This is the deployable AgentGuard control and enforcement service.

Current entry point:

```bash
agentguard-api
```

or:

```bash
python -m uvicorn agentguard.server.app:app --host 0.0.0.0 --port 8000
```

The FastAPI implementation lives under `src/agentguard/server`. The future remote
interception API will be added to this service.
