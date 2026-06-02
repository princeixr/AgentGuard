"""Google ADK helpers for emitting canonical AgentGuard v1 traces."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentguard.core.models import ExecutedToolCall
from agentguard.governance.firewall_v1 import AgentGuardFirewallV1
from agentguard.runtime.tool_event_mapper import infer_tool_category
from agentguard.tracing.schema_v1 import AgentGuardTraceV1, LiveEventV1, TraceSourceV1
from agentguard.tracing.trace_store import TraceStore
from agentguard.tracing.trace_v1_builder import TraceV1BuildInput, TraceV1Builder


class GoogleADKAdapter:
    def __init__(self, tool_registry=None, firewall=None, trace_builder=None, trace_store=None, max_steps=6):
        self.tool_registry = tool_registry
        self.firewall = firewall or AgentGuardFirewallV1(trace_store=trace_store)
        self.trace_builder = trace_builder
        self.trace_store = trace_store
        self.max_steps = max_steps

    def run_session(self, scenario_id: str) -> list[AgentGuardTraceV1]:
        raise NotImplementedError(
            "Google ADK integration will emit AgentGuardTraceV1 records and call "
            "AgentGuardFirewallV1 before MCP tool execution."
        )


class GoogleADKTraceSession:
    """Stateful adapter from ADK function-call events to AgentGuardTraceV1 JSONL.

    The ADK standalone chat loop receives a user message, then model events containing
    function calls and function responses. This class keeps just enough per-session
    state to build one canonical trace for each proposed tool call.
    """

    def __init__(
        self,
        session_id: str,
        agent_id: str,
        available_tools: list[str],
        trace_store: TraceStore | None = None,
        namespace: str = "google_adk",
        agent_config_id: str | None = None,
        environment_id: str | None = None,
        runtime_agent_id: str | None = None,
        trace_root: Path | str | None = None,
        builder: TraceV1Builder | None = None,
    ):
        self.session_id = session_id
        self.agent_id = agent_id
        self.available_tools = available_tools
        self.namespace = namespace
        self.agent_config_id = agent_config_id
        self.environment_id = environment_id
        self.runtime_agent_id = runtime_agent_id or agent_id
        self.trace_store = trace_store or TraceStore(root_dir=Path(trace_root or "data/traces"))
        self.builder = builder or TraceV1Builder()
        self.raw_user_request = ""
        self.prior_tool_calls: list[ExecutedToolCall] = []
        self.previous_trace_id: str | None = None
        self.previous_output_summary: str | None = None
        self.pending_traces: dict[str, AgentGuardTraceV1] = {}

    @property
    def trace_path(self) -> Path:
        return self.trace_store.root_dir / "v1" / self.namespace / "traces.jsonl"

    def start_turn(self, raw_user_request: str) -> None:
        self.raw_user_request = raw_user_request

    def record_tool_call(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        call_id: str | None = None,
    ) -> AgentGuardTraceV1:
        call_id = call_id or str(uuid4())
        args = dict(arguments or {})
        domain = _infer_domain(tool_name)
        trace = self.builder.build(
            TraceV1BuildInput(
                session_id=self.session_id,
                step_index=len(self.prior_tool_calls) + len(self.pending_traces) + 1,
                source=TraceSourceV1(
                    mode="live",
                    agent_framework="google_adk",
                    source_type="live_google_adk",
                    agent_id=self.agent_id,
                    runtime_agent_id=self.runtime_agent_id,
                    agent_config_id=self.agent_config_id,
                    environment_id=self.environment_id,
                ),
                raw_user_request=self.raw_user_request,
                normalized_intent=self.raw_user_request,
                domain=domain,
                task_category=_infer_task_category(tool_name, domain),
                tool_name=tool_name,
                arguments=args,
                call_id=call_id,
                previous_trace_id=self.previous_trace_id,
                available_tools=self.available_tools,
                task_relevant_tools=_infer_task_relevant_tools(tool_name, self.available_tools),
                confirmation_required_tools=_confirmation_required_tools(tool_name),
                prior_tool_calls=list(self.prior_tool_calls),
                previous_output_summary=self.previous_output_summary,
                execution_status="proposed",
            )
        )
        self.trace_store.append_trace_v1(trace, namespace=self.namespace)
        self._append_event("tool_proposed", trace, {"call_id": call_id})
        self.pending_traces[call_id] = trace
        return trace

    def record_tool_response(
        self,
        tool_name: str,
        response: Any,
        call_id: str | None = None,
    ) -> None:
        trace = self._pop_pending_trace(tool_name=tool_name, call_id=call_id)
        if trace is None:
            return

        status = _execution_status(response)
        output_summary = _summarize_tool_response(response)
        self.prior_tool_calls.append(
            ExecutedToolCall(
                call_id=trace.proposed_tool_call.call_id,
                session_id=self.session_id,
                step_index=trace.step_index,
                tool_name=trace.proposed_tool_call.tool_name,
                arguments=trace.proposed_tool_call.arguments,
                output_summary=output_summary,
                status=status,
            )
        )
        self.previous_trace_id = trace.trace_id
        self.previous_output_summary = output_summary
        self._append_event(
            "tool_failed" if status == "failed" else "tool_executed",
            trace,
            {"call_id": trace.proposed_tool_call.call_id, "output_summary": output_summary},
        )

    def _pop_pending_trace(
        self,
        tool_name: str,
        call_id: str | None,
    ) -> AgentGuardTraceV1 | None:
        if call_id and call_id in self.pending_traces:
            return self.pending_traces.pop(call_id)
        for pending_call_id, trace in list(self.pending_traces.items()):
            if trace.proposed_tool_call.tool_name == tool_name:
                return self.pending_traces.pop(pending_call_id)
        return None

    def _append_event(
        self,
        event_type: str,
        trace: AgentGuardTraceV1,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.trace_store.append_live_event_v1(
            LiveEventV1(
                event_id=str(uuid4()),
                event_type=event_type,
                trace_id=trace.trace_id,
                session_id=trace.session_id,
                step_index=trace.step_index,
                agent_framework="google_adk",
                agent_id=self.agent_id,
                payload=payload or {},
            ),
            namespace=self.namespace,
        )


def _infer_domain(tool_name: str) -> str:
    category = infer_tool_category(tool_name)
    return category if category != "unknown" else "tool"


def _infer_task_category(tool_name: str, domain: str) -> str:
    if tool_name == "run_shell_command":
        return "command_execution"
    return f"{domain}_tool_call"


def _infer_task_relevant_tools(tool_name: str, available_tools: list[str]) -> list[str]:
    if tool_name in available_tools:
        return [tool_name]
    return available_tools


def _confirmation_required_tools(tool_name: str) -> list[str]:
    if tool_name == "run_shell_command":
        return [tool_name]
    return []


def _execution_status(response: Any) -> str:
    if isinstance(response, Mapping):
        if response.get("error"):
            return "failed"
        if response.get("timed_out"):
            return "failed"
        exit_code = response.get("exit_code")
        if exit_code not in (None, 0):
            return "failed"
    return "executed"


def _summarize_tool_response(response: Any, max_chars: int = 500) -> str:
    if isinstance(response, Mapping):
        pieces = []
        if "exit_code" in response:
            pieces.append(f"exit_code={response.get('exit_code')}")
        stdout = str(response.get("stdout") or "").strip()
        stderr = str(response.get("stderr") or "").strip()
        if stdout:
            pieces.append(f"stdout={stdout[:max_chars]}")
        if stderr:
            pieces.append(f"stderr={stderr[:max_chars]}")
        if response.get("timed_out"):
            pieces.append("timed_out=true")
        return "; ".join(pieces) or "tool returned an empty response"
    text = str(response).strip()
    return text[:max_chars] if text else "tool returned an empty response"
