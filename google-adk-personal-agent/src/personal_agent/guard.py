"""Thin AgentGuard SDK integration for Google ADK callbacks."""

from __future__ import annotations

import time
from typing import Any, Callable

from agentguard_sdk import (
    AgentRegistration,
    AgentGuardClient,
    HttpAgentGuardClient,
    OutcomeReport,
    ToolProposal,
    TurnStart,
    administrator_rejection_message,
    agent_facing_enforcement_message,
)

from personal_agent.settings import settings


def build_guard_client() -> AgentGuardClient:
    return HttpAgentGuardClient(
        base_url=settings.agentguard_base_url,
        api_key=settings.agentguard_api_key,
        timeout_seconds=settings.agentguard_request_timeout_seconds,
        fail_closed=True,
    )


class AgentGuardAdkInterceptor:
    def __init__(
        self,
        client: AgentGuardClient,
        registration_factory: Callable[[], AgentRegistration] | None = None,
    ):
        self.client = client
        self.registration_factory = registration_factory
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
        turn_id = _turn_id(context_obj)
        session_id = _guard_session_id(context_obj)
        if self.registration_factory is not None:
            self.client.register(self.registration_factory())
        if turn_id not in self._intent_by_turn:
            result = self.client.start_turn(
                TurnStart(
                    workspace_id=settings.workspace_id,
                    agent_id=settings.agent_id,
                    deployment_id=settings.deployment_id,
                    integration_id=settings.integration_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    user_request=_user_text(context_obj),
                    manifest_version="development",
                )
            )
            self._intent_by_turn[turn_id] = result.intent_id
        call_id = getattr(context_obj, "function_call_id", None) or (
            f"{turn_id}:{_tool_name(tool)}"
        )
        started = time.perf_counter()
        decision = self.client.evaluate(
            ToolProposal(
                workspace_id=settings.workspace_id,
                agent_id=settings.agent_id,
                deployment_id=settings.deployment_id,
                integration_id=settings.integration_id,
                session_id=session_id,
                turn_id=turn_id,
                intent_id=self._intent_by_turn[turn_id],
                call_id=call_id,
                tool_name=_tool_name(tool),
                arguments=args,
            )
        )
        self._decision_by_call[call_id] = (decision.decision_id, started)
        approval = None
        if decision.decision == "require_approval" and settings.enforce_approval:
            if decision.approval_request_id:
                try:
                    approval = self.client.wait_for_approval(
                        decision.approval_request_id,
                        timeout_seconds=settings.approval_wait_timeout_seconds,
                        poll_interval_seconds=settings.approval_poll_interval_seconds,
                    )
                except AttributeError:
                    approval = None
            if approval is not None and approval.status == "approved":
                return None

        should_stop = decision.decision in {"block", "require_approval"}
        if should_stop:
            rejected = approval is not None and approval.status == "rejected"
            agent_message = (
                administrator_rejection_message()
                if rejected
                else agent_facing_enforcement_message(
                    decision.decision,
                    decision.matched_rules,
                )
            )
            self.client.report_outcome(
                OutcomeReport(
                    decision_id=decision.decision_id,
                    call_id=call_id,
                    status="blocked",
                    output_summary=agent_message,
                )
            )
            return {
                "blocked_by_agentguard": True,
                "approval_required": decision.decision == "require_approval" and not rejected,
                "decision": "block" if rejected else decision.decision,
                "explanation": agent_message,
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
        response_payload = tool_response if tool_response is not None else response
        self._report(tool, context_obj, "executed", str(response_payload)[:1000])

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


def _guard_session_id(context) -> str:
    """Use one AgentGuard session per ADK invocation.

    ADK keeps the same chat session across many user turns. AgentGuard sessions
    represent one governed user request, so combining the chat and invocation
    identities prevents unrelated turns from being merged in trace replay.
    """
    return f"{_session_id(context)}:{_turn_id(context)}"


def _user_text(context) -> str:
    content = getattr(context, "user_content", None)
    return "".join(
        str(getattr(part, "text", "") or "")
        for part in getattr(content, "parts", None) or []
    ).strip()


def _tool_name(tool) -> str:
    return getattr(tool, "name", None) or getattr(tool, "__name__", None) or str(tool)
