"""Minimal AgentGuard SDK integration example.

Run after starting AgentGuard:

    docker compose up
    AGENTGUARD_BASE_URL=http://127.0.0.1:8000 \
    AGENTGUARD_API_KEY=dev-agentguard-key \
    python examples/minimal-python-agent/main.py
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone

from agentguard_sdk import (
    AgentRegistration,
    HttpAgentGuardClient,
    OutcomeReport,
    ToolManifest,
    ToolProposal,
    TurnStart,
)


def run_shell_command(command: str) -> str:
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return (completed.stdout or completed.stderr).strip()[:1000]


def main() -> None:
    base_url = os.environ.get("AGENTGUARD_BASE_URL", "http://127.0.0.1:8000")
    api_key = os.environ.get("AGENTGUARD_API_KEY", "dev-agentguard-key")
    client = HttpAgentGuardClient(base_url=base_url, api_key=api_key)

    registration = AgentRegistration(
        workspace_id="wsp_quickstart",
        agent_id="agt_minimal_python",
        deployment_id="dep_local",
        integration_id="int_minimal_sdk",
        name="Minimal Python Agent",
        description="Tiny SDK-only AgentGuard integration example.",
        framework="python",
        runtime_version="quickstart",
        environment="local",
        manifest_version="quickstart",
        tools=[
            ToolManifest(
                name="run_shell_command",
                source_name="run_shell_command",
                provider="local_terminal",
                framework="python",
                transport="native",
                description="Execute one local shell command.",
                input_schema={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
                annotations={
                    "agentguard": {
                        "domain": "shell",
                        "operation": "shell",
                        "capabilities": ["dynamic.shell"],
                        "risk_level": "high_risk",
                        "confidence": 1.0,
                    }
                },
                metadata_provenance=["example"],
            )
        ],
    )
    client.register(registration)

    turn = client.start_turn(
        TurnStart(
            workspace_id=registration.workspace_id,
            agent_id=registration.agent_id,
            deployment_id=registration.deployment_id,
            integration_id=registration.integration_id,
            session_id="sess_minimal_python",
            turn_id="turn_001",
            user_request="Show me the current directory.",
            manifest_version=registration.manifest_version,
        )
    )

    proposal = ToolProposal(
        workspace_id=registration.workspace_id,
        agent_id=registration.agent_id,
        deployment_id=registration.deployment_id,
        integration_id=registration.integration_id,
        session_id="sess_minimal_python",
        turn_id=turn.turn_id,
        intent_id=turn.intent_id,
        call_id="call_pwd",
        tool_name="run_shell_command",
        arguments={"command": "pwd"},
        timestamp=datetime.now(timezone.utc),
    )
    decision = client.evaluate(proposal)
    print(f"AgentGuard decision: {decision.decision}")
    print(decision.explanation)

    if decision.decision == "require_approval" and decision.approval_request_id:
        print("Waiting for approval in AgentGuard UI...")
        approval = client.wait_for_approval(decision.approval_request_id, timeout_seconds=60)
        if approval.status != "approved":
            client.report_outcome(
                OutcomeReport(
                    decision_id=decision.decision_id,
                    call_id=proposal.call_id,
                    status="blocked",
                    output_summary=f"Approval status was {approval.status}.",
                )
            )
            print(f"Tool not executed: approval status {approval.status}")
            return

    if decision.decision == "block":
        client.report_outcome(
            OutcomeReport(
                decision_id=decision.decision_id,
                call_id=proposal.call_id,
                status="blocked",
                output_summary=decision.explanation,
            )
        )
        print("Tool blocked by AgentGuard.")
        return

    output = run_shell_command("pwd")
    client.report_outcome(
        OutcomeReport(
            decision_id=decision.decision_id,
            call_id=proposal.call_id,
            status="executed",
            output_summary=output,
        )
    )
    print(f"Tool output: {output}")


if __name__ == "__main__":
    main()
