"""Execute the registered Google ADK agent from the product demo."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentguard.api.models import (
    AgentGuardTestDecision,
    AgentTestEvent,
    AgentTestRunResponse,
)
from agentguard.api.services.query import guard_evaluation_from_payload
from agentguard.control_plane.demo_adk_definition import agent_definition
from agentguard.tracing.serializers import load_jsonl


class ADKConfigurationError(RuntimeError):
    pass


class GoogleADKTestService:
    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or Path(__file__).resolve().parents[4]

    def definition(self) -> dict[str, Any]:
        self._load_environment()
        return agent_definition()

    async def run(self, message: str) -> AgentTestRunResponse:
        self._load_environment()
        if not (
            os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
        ):
            raise ADKConfigurationError(
                "Google ADK model credentials are not configured. Set GOOGLE_API_KEY "
                "in the repository .env file and restart the demo."
            )

        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        from apps.adk_agent.agent import APP_NAME, TRACE_NAMESPACE, TRACE_ROOT, root_agent

        run_id = f"run_{uuid4().hex}"
        session_id = f"web_{uuid4().hex}"
        user_id = "agentguard_demo_user"
        started = time.perf_counter()
        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )
        events: list[AgentTestEvent] = []
        final_response = ""
        content = types.Content(role="user", parts=[types.Part(text=message)])

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            event_content = getattr(event, "content", None)
            for part in getattr(event_content, "parts", None) or []:
                function_call = getattr(part, "function_call", None)
                if function_call:
                    events.append(
                        AgentTestEvent(
                            type="tool_call",
                            name=function_call.name,
                            arguments=dict(function_call.args or {}),
                        )
                    )
                function_response = getattr(part, "function_response", None)
                if function_response:
                    events.append(
                        AgentTestEvent(
                            type="tool_response",
                            name=function_response.name,
                            response=_json_value(function_response.response),
                        )
                    )
            if event.is_final_response() and event_content:
                final_response = "".join(
                    getattr(part, "text", "") or ""
                    for part in getattr(event_content, "parts", None) or []
                ).strip()
                if final_response:
                    events.append(
                        AgentTestEvent(
                            type="agent_response",
                            content=final_response,
                        )
                    )

        definition = self.definition()
        decisions = self._decisions_for_session(
            Path(TRACE_ROOT),
            TRACE_NAMESPACE,
            session_id,
        )
        return AgentTestRunResponse(
            run_id=run_id,
            session_id=session_id,
            status="completed",
            model=definition["model"],
            user_message=message,
            final_response=final_response or "The agent completed without a text response.",
            events=events,
            decisions=decisions,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )

    def _load_environment(self) -> None:
        try:
            from dotenv import load_dotenv

            load_dotenv(self.repo_root / ".env")
        except ModuleNotFoundError:
            return

    def _decisions_for_session(
        self,
        trace_root: Path,
        namespace: str,
        session_id: str,
    ) -> list[AgentGuardTestDecision]:
        namespace_root = trace_root / "v1" / namespace
        traces = {
            item["trace_id"]: item
            for item in load_jsonl(namespace_root / "traces.jsonl")
            if item.get("session_id") == session_id
        }
        v2_by_trace = {
            event["trace_id"]: event["payload"]
            for event in load_jsonl(namespace_root / "live_events.jsonl")
            if event.get("event_type") == "firewall_v2_evaluated"
            and event.get("trace_id") in traces
        }
        items = []
        for decision in load_jsonl(namespace_root / "decisions.jsonl"):
            if decision.get("trace_id") not in traces:
                continue
            trace_id = decision["trace_id"]
            v2_payload = v2_by_trace.get(trace_id, {})
            effective_decision = v2_payload.get("effective_decision") or decision
            guard_evaluation = (
                guard_evaluation_from_payload(v2_payload)
                if v2_payload
                else None
            )
            items.append(
                AgentGuardTestDecision(
                    trace_id=trace_id,
                    tool_name=traces[trace_id]["proposed_tool_call"]["tool_name"],
                    decision=effective_decision["decision"],
                    risk_score=effective_decision["final_risk_score"],
                    explanation=effective_decision["explanation"],
                    rules_fired=effective_decision.get("decision_rules_fired", []),
                    guard_evaluation=guard_evaluation,
                )
            )
        return items


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
