"""Agent-owned runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ModuleNotFoundError:
    pass


@dataclass(frozen=True)
class Settings:
    workspace_id: str = os.environ.get("AGENT_WORKSPACE_ID", "wsp_agentguard_demo")
    agent_id: str = os.environ.get("AGENT_ID", "agt_google_adk_assistant")
    deployment_id: str = os.environ.get(
        "AGENT_DEPLOYMENT_ID", "dep_google_adk_development"
    )
    integration_id: str = os.environ.get(
        "AGENT_INTEGRATION_ID", "int_google_adk_remote"
    )
    environment: str = os.environ.get("AGENT_ENVIRONMENT", "development")
    model: str = os.environ.get("ADK_MODEL", "gemini-3-flash-preview")
    agent_ui_url: str | None = os.environ.get("AGENT_UI_URL")
    mcp_config_path: Path = Path(
        os.environ.get("ADK_MCP_CONFIG_PATH", str(ROOT / "config/adk_mcp_servers.toml"))
    )
    command_timeout_seconds: int = int(
        os.environ.get("ADK_COMMAND_TIMEOUT_SECONDS", "60")
    )
    max_output_chars: int = int(os.environ.get("ADK_MAX_OUTPUT_CHARS", "20000"))
    enforce_approval: bool = os.environ.get(
        "AGENTGUARD_ENFORCE_APPROVAL", "true"
    ).lower() in {"1", "true", "yes", "on"}
    agentguard_base_url: str = os.environ.get(
        "AGENTGUARD_BASE_URL",
        "http://127.0.0.1:8000",
    )
    agentguard_api_key: str | None = os.environ.get("AGENTGUARD_API_KEY")
    agentguard_request_timeout_seconds: float = float(
        os.environ.get("AGENTGUARD_REQUEST_TIMEOUT_SECONDS", "5")
    )
    approval_wait_timeout_seconds: float = float(
        os.environ.get("AGENTGUARD_APPROVAL_WAIT_TIMEOUT_SECONDS", "60")
    )
    approval_poll_interval_seconds: float = float(
        os.environ.get("AGENTGUARD_APPROVAL_POLL_INTERVAL_SECONDS", "1")
    )


settings = Settings()
