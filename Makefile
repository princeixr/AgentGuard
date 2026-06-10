.PHONY: docker-up docker-down docker-logs test test-product test-dashboard build-dashboard sdk-example

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

test: test-product test-dashboard

test-product:
	cd agentguard-product && PYTHONPATH=src:packages/agentguard-sdk/src ../.venv/bin/python -m pytest -q

test-dashboard:
	npm --prefix agentguard-product/apps/agentguard_dashboard test

build-dashboard:
	npm --prefix agentguard-product/apps/agentguard_dashboard run build

sdk-example:
	PYTHONPATH=agentguard-product/packages/agentguard-sdk/src python examples/minimal-python-agent/main.py
