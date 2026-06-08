.PHONY: demo demo-data test test-backend test-frontend build-frontend adk-chat

demo:
	uv run python scripts/run_product_demo.py

demo-data:
	uv run python scripts/reset_demo_data.py

adk-chat:
	uv run apps/adk_agent/chat.py

test: test-backend test-frontend

test-backend:
	uv run pytest -q

test-frontend:
	npm --prefix apps/web test

build-frontend:
	npm --prefix apps/web run build
