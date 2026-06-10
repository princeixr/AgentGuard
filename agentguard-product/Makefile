.PHONY: api test test-backend test-frontend build-frontend docker-build helm-lint smoke-remote

api:
	uv run agentguard-api

test: test-backend test-frontend

test-backend:
	PYTHONPATH=src:packages/agentguard-sdk/src ../.venv/bin/python -m pytest -q

test-frontend:
	npm --prefix apps/agentguard_dashboard test

build-frontend:
	npm --prefix apps/agentguard_dashboard run build

docker-build:
	docker build -f Dockerfile.api -t agentguard-api:local .
	docker build -f Dockerfile.dashboard -t agentguard-dashboard:local .

helm-lint:
	helm lint charts/agentguard

smoke-remote:
	PYTHONPATH=packages/agentguard-sdk/src:src ../.venv/bin/python scripts/smoke_remote_approval.py
