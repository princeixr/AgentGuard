.PHONY: docker-up docker-down docker-logs test test-product test-dashboard build-dashboard sdk-example adk-agent start

start:
	make docker-down; make docker-up; make adk-agent 
docker-up:
	docker compose up --build -d
	# http://127.0.0.1:5173/
	# agent guard api : http://127.0.0.1:8002/api/docs
docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

adk-agent:
	uv run --project google-adk-personal-agent adk web --port 8001 google-adk-personal-agent/src/personal_agent
	# http://127.0.0.1:8001/dev-ui/?app=personal_agent
test: test-product test-dashboard

test-product:
	cd agentguard-product && PYTHONPATH=src:packages/agentguard-sdk/src ../.venv/bin/python -m pytest -q

test-dashboard:
	npm --prefix agentguard-product/apps/agentguard_dashboard test

build-dashboard:
	npm --prefix agentguard-product/apps/agentguard_dashboard run build

sdk-example:
	PYTHONPATH=agentguard-product/packages/agentguard-sdk/src python examples/minimal-python-agent/main.py
