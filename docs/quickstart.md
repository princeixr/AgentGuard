# Quickstart

Run AgentGuard locally with Docker Compose.

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- Optional: `GOOGLE_API_KEY` if you want Gemini-backed intent/Tier 3 evaluation

## Start AgentGuard

```bash
cp .env.local.example .env
docker compose --env-file .env up --build
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
AGENTGUARD_API_KEY="$(grep '^AGENTGUARD_API_KEY=' .env | cut -d= -f2-)" \
python examples/minimal-python-agent/main.py
```

If the decision requires approval, open the dashboard approval page and approve/reject the call.

## One-Call SDK Example

```python
from agentguard_sdk import AgentGuard

guard = AgentGuard(agent_id="my_chatbot")

decision = guard.check(
    user_message="Search the web for AgentGuard.",
    tool="web_search",
    args={"query": "AgentGuard runtime governance"},
    tool_type="web.search",
)

print(decision.decision, decision.reason)
```

The high-level SDK handles registration, turn creation, tool proposal evaluation,
and approval metadata for you.

## Stop

```bash
docker compose down
```
