# Docker Compose Deployment

```bash
export AGENTGUARD_API_KEY=replace-me
docker compose up --build -d
```

Services:

- `agentguard-api`: FastAPI API on port `8000`
- `agentguard-dashboard`: Nginx-served React app on port `5173`

Runtime data is stored in the `agentguard-data` Docker volume.

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
