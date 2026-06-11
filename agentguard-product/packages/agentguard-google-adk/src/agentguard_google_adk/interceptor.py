"""Framework adapter for Google ADK tool callbacks."""

from __future__ import annotations

import time
import os
from dataclasses import dataclass
from typing import Any

from agentguard_sdk import AgentGuardClient, HttpAgentGuardClient, OutcomeReport, ToolProposal, TurnStart


@dataclass(frozen=True)
class AgentGuardAdkSettings:
    workspace_id: str
    agent_id: str
    deployment_id: str
    integration_id: str
    manifest_version: str = "production"
    enforce_approval: bool = True
    approval_wait_timeout_seconds: float = 60.0
    approval_poll_interval_seconds: float = 1.0


class AgentGuardAdkInterceptor:
    """Google ADK callback-compatible tool interceptor."""

    def __init__(self, client: AgentGuardClient, settings: AgentGuardAdkSettings):
        self.client = client
        self.settings = settings
        self._intent_by_turn: dict[str, str] = {}
        self._decision_by_call: dict[str, tuple[str, float]] = {}

    def before_tool(
        self,
        tool,
        args: dict[str, Any],
        tool_context=None,
        context=None,
        **_kwargs,
    ):
        context_obj = tool_context or context
        if context_obj is None:
            raise TypeError("AgentGuard callback received neither tool_context nor context.")
        session_id = _session_id(context_obj)
        turn_id = _turn_id(context_obj)
        if turn_id not in self._intent_by_turn:
            result = self.client.start_turn(
                TurnStart(
                    workspace_id=self.settings.workspace_id,
                    agent_id=self.settings.agent_id,
                    deployment_id=self.settings.deployment_id,
                    integration_id=self.settings.integration_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    user_request=_user_text(context_obj),
                    manifest_version=self.settings.manifest_version,
                )
            )
            self._intent_by_turn[turn_id] = result.intent_id
        call_id = getattr(context_obj, "function_call_id", None) or f"{turn_id}:{_tool_name(tool)}"
        started = time.perf_counter()
        decision = self.client.evaluate(
            ToolProposal(
                workspace_id=self.settings.workspace_id,
                agent_id=self.settings.agent_id,
                deployment_id=self.settings.deployment_id,
                integration_id=self.settings.integration_id,
                session_id=session_id,
                turn_id=turn_id,
                intent_id=self._intent_by_turn[turn_id],
                call_id=call_id,
                tool_name=_tool_name(tool),
                arguments=args,
            )
        )
        self._decision_by_call[call_id] = (decision.decision_id, started)
        if decision.decision == "require_approval" and self.settings.enforce_approval:
            approval = None
            if decision.approval_request_id and hasattr(self.client, "wait_for_approval"):
                approval = self.client.wait_for_approval(
                    decision.approval_request_id,
                    timeout_seconds=self.settings.approval_wait_timeout_seconds,
                    poll_interval_seconds=self.settings.approval_poll_interval_seconds,
                )
            if approval is not None and approval.status == "approved":
                return None
        if decision.decision in {"block", "require_approval"}:
            self.client.report_outcome(
                OutcomeReport(
                    decision_id=decision.decision_id,
                    call_id=call_id,
                    status="blocked",
                    output_summary=decision.explanation,
                )
            )
            return {
                "blocked_by_agentguard": True,
                "approval_required": decision.decision == "require_approval",
                "decision": decision.decision,
                "explanation": decision.explanation,
                "trace_id": decision.trace_id,
            }
        return None

    def after_tool(
        self,
        tool,
        args: dict[str, Any],
        tool_context=None,
        context=None,
        tool_response=None,
        response=None,
        **_kwargs,
    ):
        context_obj = tool_context or context
        if context_obj is None:
            raise TypeError("AgentGuard callback received neither tool_context nor context.")
        payload = tool_response if tool_response is not None else response
        self._report(tool, context_obj, "executed", str(payload)[:1000])

    def on_tool_error(
        self,
        tool,
        args: dict[str, Any],
        tool_context=None,
        context=None,
        error=None,
        **_kwargs,
    ):
        context_obj = tool_context or context
        if context_obj is None:
            raise TypeError("AgentGuard callback received neither tool_context nor context.")
        self._report(tool, context_obj, "failed", str(error)[:1000])

    def _report(self, tool, context, status: str, summary: str) -> None:
        call_id = getattr(context, "function_call_id", None) or (
            f"{_turn_id(context)}:{_tool_name(tool)}"
        )
        pending = self._decision_by_call.pop(call_id, None)
        if pending is None:
            return
        decision_id, started = pending
        self.client.report_outcome(
            OutcomeReport(
                decision_id=decision_id,
                call_id=call_id,
                status=status,
                output_summary=summary,
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
        )


def protect_adk_agent(
    agent,
    *,
    client: AgentGuardClient | None = None,
    settings: AgentGuardAdkSettings | None = None,
):
    """Attach AgentGuard callbacks to an existing Google ADK agent when possible."""
    interceptor = AgentGuardAdkInterceptor(
        client or build_client_from_env(),
        settings or settings_from_env(),
    )
    for attr, callback in {
        "before_tool_callback": interceptor.before_tool,
        "after_tool_callback": interceptor.after_tool,
        "on_tool_error_callback": interceptor.on_tool_error,
    }.items():
        try:
            setattr(agent, attr, callback)
        except Exception:
            pass
    return agent


def build_client_from_env() -> HttpAgentGuardClient:
    return HttpAgentGuardClient(
        base_url=os.environ.get("AGENTGUARD_BASE_URL", "http://localhost:8000"),
        api_key=os.environ.get("AGENTGUARD_API_KEY"),
    )


def settings_from_env() -> AgentGuardAdkSettings:
    return AgentGuardAdkSettings(
        workspace_id=os.environ.get("AGENTGUARD_WORKSPACE_ID", "default"),
        agent_id=os.environ.get("AGENTGUARD_AGENT_ID", "google_adk_agent"),
        deployment_id=os.environ.get("AGENTGUARD_DEPLOYMENT_ID", "default"),
        integration_id=os.environ.get("AGENTGUARD_INTEGRATION_ID", "google_adk"),
        manifest_version=os.environ.get("AGENTGUARD_MANIFEST_VERSION", "production"),
        enforce_approval=os.environ.get("AGENTGUARD_ENFORCE_APPROVAL", "true").lower()
        in {"1", "true", "yes", "on"},
        approval_wait_timeout_seconds=float(
            os.environ.get("AGENTGUARD_APPROVAL_WAIT_TIMEOUT_SECONDS", "60")
        ),
        approval_poll_interval_seconds=float(
            os.environ.get("AGENTGUARD_APPROVAL_POLL_INTERVAL_SECONDS", "1")
        ),
    )


def _session_id(context) -> str:
    session = getattr(context, "session", None)
    return (
        getattr(session, "id", None)
        or getattr(session, "session_id", None)
        or getattr(context, "invocation_id", None)
        or "local_session"
    )


def _turn_id(context) -> str:
    return getattr(context, "invocation_id", None) or f"{_session_id(context)}:turn"


def _user_text(context) -> str:
    content = getattr(context, "user_content", None)
    return "".join(
        str(getattr(part, "text", "") or "")
        for part in getattr(content, "parts", None) or []
    ).strip()


def _tool_name(tool) -> str:
    return getattr(tool, "name", None) or getattr(tool, "__name__", None) or str(tool)
