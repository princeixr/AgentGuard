# Quickstart

```bash
cp .env.local.example .env
docker compose --env-file .env up --build
```

Open:

- Dashboard: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/api/docs`

Install the SDK:

```bash
pip install agentguard-sdk
```

Local development from this repo:

```bash
pip install -e agentguard-product/packages/agentguard-sdk
```
