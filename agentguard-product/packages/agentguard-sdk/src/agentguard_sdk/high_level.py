"""High-level AgentGuard SDK ergonomics for custom chatbots."""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from agentguard_sdk.client import HttpAgentGuardClient
from agentguard_sdk.models import (
    AgentRegistration,
    GuardCheck,
    GuardCheckResult,
    OutcomeReport,
    ToolManifest,
)
from agentguard_sdk.tool_registry import manifest_from_tool


class AgentGuard:
    """Small high-level facade over AgentGuard's low-level runtime API."""

    def __init__(
        self,
        *,
        agent_id: str,
        base_url: str | None = None,
        api_key: str | None = None,
        workspace_id: str = "default",
        deployment_id: str = "default",
        integration_id: str = "default",
        framework: str = "custom",
        runtime_version: str = "unknown",
        environment: str = "production",
        approval_mode: str = "async",
        fail_closed: bool = True,
    ):
        self.agent_id = agent_id
        self.workspace_id = workspace_id
        self.deployment_id = deployment_id
        self.integration_id = integration_id
        self.framework = framework
        self.runtime_version = runtime_version
        self.environment = environment
        self.approval_mode = approval_mode
        self.client = HttpAgentGuardClient(
            base_url=base_url or os.environ.get("AGENTGUARD_BASE_URL", "http://localhost:8000"),
            api_key=api_key or os.environ.get("AGENTGUARD_API_KEY"),
            fail_closed=fail_closed,
        )
        self._tools: dict[str, ToolManifest] = {}

    def register_tool(
        self,
        name: str,
        *,
        tool_type: str | None = None,
        description: str | None = None,
        input_schema: dict[str, Any] | None = None,
        metadata_overrides: dict[str, Any] | None = None,
    ) -> ToolManifest:
        manifest = manifest_from_tool(
            name,
            tool_type=tool_type,
            description=description,
            input_schema=input_schema,
            framework=self.framework,
            metadata_overrides=metadata_overrides,
        )
        self._tools[name] = manifest
        self.client.register(self._registration())
        return manifest

    def register_tools(self, tools: list[str]) -> None:
        for tool_name in tools:
            self._tools[tool_name] = manifest_from_tool(tool_name, framework=self.framework)
        self.client.register(self._registration())

    def check(
        self,
        *,
        user_message: str,
        tool: str,
        args: dict[str, Any] | None = None,
        tool_type: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        call_id: str | None = None,
        approval_mode: str | None = None,
        metadata_overrides: dict[str, Any] | None = None,
    ) -> GuardCheckResult:
        if tool not in self._tools:
            self.register_tool(
                tool,
                tool_type=tool_type,
                metadata_overrides=metadata_overrides,
            )
        result = self.client.check(
            GuardCheck(
                workspace_id=self.workspace_id,
                agent_id=self.agent_id,
                deployment_id=self.deployment_id,
                integration_id=self.integration_id,
                session_id=session_id,
                turn_id=turn_id,
                call_id=call_id,
                user_message=user_message,
                tool_name=tool,
                arguments=args or {},
                tool_type=tool_type,
                framework=self.framework,
                runtime_version=self.runtime_version,
                environment=self.environment,
                metadata_overrides=metadata_overrides or {},
                approval_mode=approval_mode or self.approval_mode,
            )
        )
        if (
            result.requires_approval
            and (approval_mode or self.approval_mode) == "wait"
            and result.approval_id
        ):
            approval = self.client.wait_for_approval(result.approval_id)
            if approval.status == "approved":
                return result.model_copy(
                    update={
                        "allowed": True,
                        "requires_approval": False,
                        "decision": "allow",
                        "reason": "Approved by AgentGuard operator.",
                    }
                )
        return result

    def tool(
        self,
        *,
        tool_type: str | None = None,
        user_message_arg: str = "user_message",
        metadata_overrides: dict[str, Any] | None = None,
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.register_tool(
                func.__name__,
                tool_type=tool_type,
                description=func.__doc__ or None,
                metadata_overrides=metadata_overrides,
            )

            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                user_message = str(kwargs.pop(user_message_arg, "") or "User request unavailable.")
                call_id = f"call_{uuid4().hex}"
                decision = self.check(
                    user_message=user_message,
                    tool=func.__name__,
                    args=dict(kwargs),
                    tool_type=tool_type,
                    call_id=call_id,
                    approval_mode="wait",
                    metadata_overrides=metadata_overrides,
                )
                if not decision.allowed:
                    self.client.report_outcome(
                        OutcomeReport(
                            decision_id=decision.decision_id,
                            call_id=decision.call_id,
                            status="blocked",
                            output_summary=decision.reason,
                        )
                    )
                    raise PermissionError(decision.reason)
                try:
                    output = func(*args, **kwargs)
                except Exception as exc:
                    self.client.report_outcome(
                        OutcomeReport(
                            decision_id=decision.decision_id,
                            call_id=decision.call_id,
                            status="failed",
                            output_summary=str(exc)[:1000],
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    )
                    raise
                self.client.report_outcome(
                    OutcomeReport(
                        decision_id=decision.decision_id,
                        call_id=decision.call_id,
                        status="executed",
                        output_summary=str(output)[:1000],
                    )
                )
                return output

            return wrapped

        return decorator

    def _registration(self) -> AgentRegistration:
        return AgentRegistration(
            workspace_id=self.workspace_id,
            agent_id=self.agent_id,
            deployment_id=self.deployment_id,
            integration_id=self.integration_id,
            name=self.agent_id,
            description=f"AgentGuard SDK integration for {self.agent_id}.",
            framework=self.framework,
            runtime_version=self.runtime_version,
            environment=self.environment,
            manifest_version="v2",
            tools=list(self._tools.values()),
        )
