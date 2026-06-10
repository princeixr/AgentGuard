# Quickstart

Run AgentGuard locally with Docker Compose.

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- Optional: `GOOGLE_API_KEY` if you want Gemini-backed intent/Tier 3 evaluation

## Start AgentGuard

```bash
export AGENTGUARD_API_KEY=dev-agentguard-key
docker compose up --build
```

Open:

- AgentGuard dashboard: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/api/docs

## Run the Minimal SDK Example

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e agentguard-product/packages/agentguard-sdk
AGENTGUARD_BASE_URL=http://127.0.0.1:8000 \
AGENTGUARD_API_KEY=dev-agentguard-key \
python examples/minimal-python-agent/main.py
```

If the decision requires approval, open the dashboard approval page and approve/reject the call.

## Stop

```bash
docker compose down
```
