.PHONY: api demo demo-data test test-backend test-frontend build-frontend adk-chat

api:
	uv run agentguard-api

demo:
	uv run python scripts/run_product_demo.py

demo-data:
	uv run python scripts/reset_demo_data.py

adk-chat:
	uv run examples/google_adk_agent/chat.py

test: test-backend test-frontend

test-backend:
	uv run pytest -q

test-frontend:
	npm --prefix apps/agentguard_dashboard test

build-frontend:
	npm --prefix apps/agentguard_dashboard run build
