"""Framework-neutral registered-agent repository used by the local product demo."""

from __future__ import annotations

import json
from pathlib import Path

from agentguard.control_plane.models import (
    AgentRecord,
    RegisteredAgentDefinition,
    RuntimeIdentity,
    UserRecord,
    WorkspaceRecord,
)


class AgentRegistry:
    def __init__(self, fixture_path: Path | str | None = None):
        path = Path(fixture_path) if fixture_path else _default_fixture_path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.workspace = WorkspaceRecord.model_validate(payload["workspace"])
        self.user = UserRecord.model_validate(payload["user"])
        self._agents = {
            item["agent_id"]: AgentRecord.model_validate(item)
            for item in payload["agents"]
        }
        self._definitions = {
            item["agent_id"]: RegisteredAgentDefinition.model_validate(item)
            for item in payload["definitions"]
        }

    def list_agents(self, workspace_id: str) -> list[AgentRecord]:
        return [
            agent
            for agent in self._agents.values()
            if agent.workspace_id == workspace_id
        ]

    def get_agent(self, workspace_id: str, agent_id: str) -> AgentRecord | None:
        agent = self._agents.get(agent_id)
        if agent is None or agent.workspace_id != workspace_id:
            return None
        return agent

    def definition(self, agent_id: str) -> RegisteredAgentDefinition | None:
        return self._definitions.get(agent_id)

    def runtime_identity(self, agent_id: str) -> RuntimeIdentity:
        agent = self.get_agent(self.workspace.workspace_id, agent_id)
        definition = self.definition(agent_id)
        if agent is None or definition is None:
            raise KeyError(agent_id)
        return RuntimeIdentity(
            workspace_id=agent.workspace_id,
            agent_id=agent.agent_id,
            deployment_id=definition.deployment_id,
            integration_id=definition.integration_id,
        )


def _default_fixture_path() -> Path:
    return Path(__file__).resolve().parents[3] / "demo" / "registered_agents.json"
