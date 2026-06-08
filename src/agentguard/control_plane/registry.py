"""Seeded control plane used by the local product demo."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from agentguard.control_plane.models import (
    AgentRecord,
    DeploymentRecord,
    RuntimeIdentity,
    UserRecord,
    WorkspaceRecord,
)

DEMO_WORKSPACE_ID = "wsp_agentguard_demo"
DEMO_USER_ID = "usr_demo_owner"
DEMO_AGENT_ID = "agt_google_adk_assistant"
DEMO_DEPLOYMENT_ID = "dep_google_adk_development"
DEMO_INTEGRATION_ID = "int_google_adk_local"
DEMO_POLICY_ID = "pol_personal_assistant"
DEMO_TIMESTAMP = datetime(2026, 6, 6, 14, 30, tzinfo=timezone.utc)


class DemoAgentRegistry:
    def __init__(self):
        model_configured = bool(
            os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
        )
        deployment = DeploymentRecord(
            deployment_id=DEMO_DEPLOYMENT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
            agent_id=DEMO_AGENT_ID,
            environment="development",
            runtime_framework="google_adk",
            runtime_agent_name="terminal_assistant",
            version="adk-terminal-assistant",
            status="live" if model_configured else "offline",
            last_seen_at=DEMO_TIMESTAMP,
            metadata={"integration": "callback", "storage": "local"},
        )
        self.workspace = WorkspaceRecord(
            workspace_id=DEMO_WORKSPACE_ID,
            name="AgentGuard Demo Workspace",
            plan="Enterprise Demo",
            created_at=DEMO_TIMESTAMP,
        )
        self.user = UserRecord(
            user_id=DEMO_USER_ID,
            workspace_id=DEMO_WORKSPACE_ID,
            name="Demo Owner",
            email="owner@agentguard.local",
            role="owner",
        )
        self._agents = {
            DEMO_AGENT_ID: AgentRecord(
                agent_id=DEMO_AGENT_ID,
                workspace_id=DEMO_WORKSPACE_ID,
                name="Google ADK Assistant",
                description=(
                    "Personal productivity assistant with guarded terminal, communication, "
                    "workspace, scheduling, and future MCP capabilities."
                ),
                framework="google_adk",
                status="live" if model_configured else "setup_required",
                created_at=DEMO_TIMESTAMP,
                created_by=DEMO_USER_ID,
                default_policy_id=DEMO_POLICY_ID,
                last_seen_at=DEMO_TIMESTAMP,
                metadata={
                    "integration_status": "configured",
                    "authentication": "demo session",
                    "model_credentials_configured": model_configured,
                },
                deployments=[deployment],
            )
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

    def runtime_identity(self, agent_id: str) -> RuntimeIdentity:
        agent = self.get_agent(DEMO_WORKSPACE_ID, agent_id)
        if agent is None:
            raise KeyError(agent_id)
        deployment = agent.deployments[0]
        return RuntimeIdentity(
            workspace_id=DEMO_WORKSPACE_ID,
            agent_id=agent.agent_id,
            deployment_id=deployment.deployment_id,
            integration_id=DEMO_INTEGRATION_ID,
        )
