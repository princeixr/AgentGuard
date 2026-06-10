# syntax=docker/dockerfile:1.7
# Build with repository root as context:
# docker build -f google-adk-personal-agent/Dockerfile .
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY agentguard-product/packages/agentguard-sdk /tmp/agentguard-sdk
RUN pip install /tmp/agentguard-sdk

COPY google-adk-personal-agent/pyproject.toml google-adk-personal-agent/README.md ./
COPY google-adk-personal-agent/src ./src
COPY google-adk-personal-agent/config ./config
RUN pip install .

CMD ["python", "-m", "personal_agent.chat"]
