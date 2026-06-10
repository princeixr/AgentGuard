"""Framework-neutral registered-agent repository used by the local product demo."""

from __future__ import annotations

import json
import os
from pathlib import Path

from agentguard.control_plane.models import (
    AgentRecord,
    DeploymentRecord,
    RegisteredTool,
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

    def register(self, registration) -> AgentRecord:
        """Register or refresh a remote agent manifest.

        The registry is intentionally process-local for the first production
        transport cut. Durable persistence belongs in the database-backed control
        plane, but this keeps live interception independent from demo fixtures.
        """
        workspace_id = registration.workspace_id
        if workspace_id != self.workspace.workspace_id:
            self.workspace = WorkspaceRecord(
                workspace_id=workspace_id,
                name=workspace_id,
                plan="Open Source",
            )
        deployment = DeploymentRecord(
            deployment_id=registration.deployment_id,
            workspace_id=workspace_id,
            agent_id=registration.agent_id,
            environment=registration.environment,
            runtime_framework=registration.framework,
            runtime_agent_name=registration.name,
            version=registration.runtime_version,
            status="live",
        )
        record = AgentRecord(
            agent_id=registration.agent_id,
            workspace_id=workspace_id,
            name=registration.name,
            description=registration.description,
            framework=registration.framework,
            status="live",
            created_by=self.user.user_id,
            default_policy_id="pol_personal_assistant",
            deployments=[deployment],
            metadata={"manifest_version": registration.manifest_version},
        )
        definition = RegisteredAgentDefinition(
            agent_id=registration.agent_id,
            deployment_id=registration.deployment_id,
            integration_id=registration.integration_id,
            framework=registration.framework,
            runtime_version=registration.runtime_version,
            environment=registration.environment,
            manifest_version=registration.manifest_version,
            system_instruction_hash=registration.system_instruction_hash,
            system_instruction_summary=registration.system_instruction_summary,
            agent_ui_url=registration.agent_ui_url,
            tools=[
                RegisteredTool(
                    name=tool.name,
                    description=tool.description,
                    source_name=tool.source_name,
                    provider=tool.provider,
                    framework=tool.framework,
                    transport=tool.transport,
                    input_schema=tool.input_schema,
                    annotations=tool.annotations,
                    metadata_provenance=tool.metadata_provenance,
                )
                for tool in registration.tools
            ],
        )
        self._agents[registration.agent_id] = record
        self._definitions[registration.agent_id] = definition
        return record

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
    configured = os.environ.get("AGENTGUARD_REGISTERED_AGENTS_PATH")
    if configured:
        return Path(configured)
    candidates = [
        Path.cwd() / "demo" / "registered_agents.json",
        Path(__file__).resolve().parents[3] / "demo" / "registered_agents.json",
        Path("/app/demo/registered_agents.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
