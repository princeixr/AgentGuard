"""Configuration helpers for local development."""

from pydantic import BaseModel


class AgentGuardConfig(BaseModel):
    runtime: str = "mock"
    max_steps: int = 6
    trace_dir: str = "data/traces/raw"
    scenario_dir: str = "data/scenarios"
    seed_memory_dir: str = "data/seed_memory"
    use_mock_tools: bool = True
    enable_approval_simulation: bool = False


def load_config() -> AgentGuardConfig:
    return AgentGuardConfig()
