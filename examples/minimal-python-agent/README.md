# Minimal Python Agent Example

This example shows the full AgentGuard SDK loop without Google ADK or any agent framework.

## Run

Start AgentGuard first:

```bash
docker compose up --build
```

In another terminal:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e agentguard-product/packages/agentguard-sdk
AGENTGUARD_BASE_URL=http://127.0.0.1:8000 \
AGENTGUARD_API_KEY=dev-agentguard-key \
python examples/minimal-python-agent/main.py
```

If AgentGuard returns `require_approval`, open `http://127.0.0.1:5173/approvals` and approve or reject the pending tool call.
