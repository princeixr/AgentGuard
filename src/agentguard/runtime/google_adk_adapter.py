"""Google ADK helpers for emitting canonical AgentGuard v1 traces."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentguard.control_plane.models import RuntimeIdentity
from agentguard.core.enums import ToolRiskLevel
from agentguard.core.models import ExecutedToolCall
from agentguard.firewall_v2.engine import AgentGuardFirewallV2
from agentguard.firewall_v2.models import FirewallMode, FirewallV2Evaluation
from agentguard.governance.decision_policy_v1 import DecisionPolicyV1
from agentguard.governance.firewall_v1 import AgentGuardFirewallV1, FirewallResultV1
from agentguard.runtime.tool_registry import ToolMetadata, infer_tool_metadata
from agentguard.tracing.schema_v1 import AgentGuardTraceV1, LiveEventV1, TraceSourceV1
from agentguard.tracing.trace_store import TraceStore
from agentguard.tracing.trace_v1_builder import TraceV1BuildInput, TraceV1Builder

GMAIL_SEND_TOOL_NAMES = {"gmail_send", "gmail_send_email", "gmail_send_draft"}


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
        firewall: AgentGuardFirewallV1 | None = None,
        tool_metadata: dict[str, ToolMetadata] | None = None,
        enable_elastic: bool | None = None,
        fail_on_elastic_error: bool = False,
        runtime_identity: RuntimeIdentity | None = None,
        force_block: bool = False,
        firewall_mode: FirewallMode = "v1",
    ):
        self.session_id = session_id
        self.agent_id = agent_id
        self.available_tools = available_tools
        self.namespace = namespace
        self.agent_config_id = agent_config_id
        self.environment_id = environment_id
        self.runtime_agent_id = runtime_agent_id or agent_id
        self.runtime_identity = runtime_identity
        self.trace_store = trace_store or TraceStore(root_dir=Path(trace_root or "data/traces"))
        self.builder = builder or TraceV1Builder()
        self.firewall = firewall or AgentGuardFirewallV1(
            trace_store=self.trace_store,
            namespace=self.namespace,
            enable_elastic=enable_elastic,
            fail_on_elastic_error=fail_on_elastic_error,
            decision_policy=DecisionPolicyV1(force_block=force_block),
        )
        self.tool_metadata = tool_metadata or build_adk_tool_metadata(available_tools)
        self.raw_user_request = ""
        self.prior_tool_calls: list[ExecutedToolCall] = []
        self.previous_trace_id: str | None = None
        self.previous_output_summary: str | None = None
        self.pending_results: dict[str, FirewallResultV1] = {}
        self.firewall_mode = firewall_mode
        self.force_block = force_block
        self.firewall_v2 = (
            AgentGuardFirewallV2(mode=firewall_mode)
            if firewall_mode in {"v2_shadow", "v2"}
            else None
        )

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
    ) -> FirewallResultV1:
        call_id = call_id or str(uuid4())
        args = dict(arguments or {})
        metadata = self._metadata(tool_name)
        domain = _infer_domain(metadata)
        trace = self.builder.build(
            TraceV1BuildInput(
                session_id=self.session_id,
                step_index=len(self.prior_tool_calls) + len(self.pending_results) + 1,
                source=TraceSourceV1(
                    mode="live",
                    agent_framework="google_adk",
                    source_type="live_google_adk",
                    agent_id=(
                        self.runtime_identity.agent_id
                        if self.runtime_identity
                        else self.agent_id
                    ),
                    workspace_id=(
                        self.runtime_identity.workspace_id
                        if self.runtime_identity
                        else None
                    ),
                    deployment_id=(
                        self.runtime_identity.deployment_id
                        if self.runtime_identity
                        else None
                    ),
                    integration_id=(
                        self.runtime_identity.integration_id
                        if self.runtime_identity
                        else None
                    ),
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
                intent_forbidden_tools=_infer_intent_forbidden_tools(
                    tool_name,
                    self.available_tools,
                    self.raw_user_request,
                ),
                confirmation_required_tools=_confirmation_required_tools(tool_name, metadata),
                prior_tool_calls=list(self.prior_tool_calls),
                previous_output_summary=self.previous_output_summary,
                execution_status="proposed",
                mcp_server=metadata.mcp_server,
                tool_category=metadata.category,
                risk_level=metadata.risk_level.value
                if hasattr(metadata.risk_level, "value")
                else str(metadata.risk_level),
                side_effect_type=metadata.side_effect_type,
            )
        )
        result = self.firewall.intercept(trace)
        if self.firewall_v2 is not None:
            evaluation = self.firewall_v2.evaluate(trace)
            v1_decision = result.decision
            effective_decision = (
                result.decision
                if self.force_block
                else _decision_from_v2(result, evaluation)
                if self.firewall_mode == "v2"
                else result.decision
            )
            enforced_by = (
                "emergency_force_block"
                if self.force_block
                else "firewall_v2"
                if self.firewall_mode == "v2"
                else "firewall_v1"
            )
            result = FirewallResultV1(
                trace=result.trace,
                feature=result.feature,
                score=result.score,
                decision=effective_decision,
                session_state_id=result.session_state_id,
            )
            self._append_event(
                "firewall_v2_evaluated",
                trace,
                {
                    "runtime_event_source": "google_adk_adapter",
                    "enforced_by": enforced_by,
                    "enforced_decision": effective_decision.decision,
                    "v1_decision": v1_decision.model_dump(
                        mode="json",
                        by_alias=True,
                    ),
                    "effective_decision": effective_decision.model_dump(
                        mode="json",
                        by_alias=True,
                    ),
                    "firewall_mode": self.firewall_mode,
                    "evaluation": evaluation.model_dump(mode="json", by_alias=True),
                },
            )
        self.pending_results[call_id] = result
        return result

    def record_tool_response(
        self,
        tool_name: str,
        response: Any,
        call_id: str | None = None,
    ) -> None:
        result = self._pop_pending_result(tool_name=tool_name, call_id=call_id)
        if result is None:
            return
        trace = result.trace

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
        event_type = {
            "blocked": "tool_blocked",
            "failed": "tool_failed",
        }.get(status, "tool_executed")
        self._append_event(
            event_type,
            trace,
            _runtime_event_payload(
                result=result,
                execution_status=status,
                output_summary=output_summary,
            ),
        )

    def _pop_pending_result(
        self,
        tool_name: str,
        call_id: str | None,
    ) -> FirewallResultV1 | None:
        if call_id and call_id in self.pending_results:
            return self.pending_results.pop(call_id)
        for pending_call_id, result in list(self.pending_results.items()):
            if result.trace.proposed_tool_call.tool_name == tool_name:
                return self.pending_results.pop(pending_call_id)
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
                agent_id=trace.source.agent_id,
                workspace_id=trace.source.workspace_id,
                deployment_id=trace.source.deployment_id,
                integration_id=trace.source.integration_id,
                payload=payload or {},
            ),
            namespace=self.namespace,
        )

    def _metadata(self, tool_name: str) -> ToolMetadata:
        return self.tool_metadata.get(tool_name, infer_adk_tool_metadata(tool_name))


def build_adk_tool_metadata(available_tools: list[str]) -> dict[str, ToolMetadata]:
    return {tool_name: infer_adk_tool_metadata(tool_name) for tool_name in available_tools}


def infer_adk_tool_metadata(tool_name: str) -> ToolMetadata:
    if tool_name == "run_shell_command":
        return ToolMetadata(
            name=tool_name,
            category="shell",
            risk_level=ToolRiskLevel.LOW_SIDE_EFFECT,
            side_effect_type="shell_command",
            requires_confirmation_by_default=False,
            irreversible=False,
            description="Run a local non-interactive shell command.",
        )
    if tool_name.startswith("gmail_"):
        raw_gmail_tool = tool_name.removeprefix("gmail_")
        if raw_gmail_tool in {"search", "search_emails", "read", "read_email"}:
            risk_level = ToolRiskLevel.READ_ONLY
            side_effect_type = None
            requires_confirmation = False
            irreversible = False
        elif raw_gmail_tool in {"draft", "draft_email"}:
            risk_level = ToolRiskLevel.LOW_SIDE_EFFECT
            side_effect_type = "local_draft_create"
            requires_confirmation = False
            irreversible = False
        elif raw_gmail_tool in {"send", "send_email", "send_draft"}:
            risk_level = ToolRiskLevel.EXTERNAL_WRITE
            side_effect_type = "external_message_send"
            requires_confirmation = True
            irreversible = True
        else:
            risk_level = ToolRiskLevel.LOW_SIDE_EFFECT
            side_effect_type = None
            requires_confirmation = False
            irreversible = False
        return ToolMetadata(
            name=tool_name,
            category="email",
            risk_level=risk_level,
            side_effect_type=side_effect_type,
            requires_confirmation_by_default=requires_confirmation,
            irreversible=irreversible,
            mcp_server="artymclabin_gmail_mcp",
            description=f"Gmail MCP tool {raw_gmail_tool}.",
        )
    return infer_tool_metadata(tool_name)


def _infer_domain(metadata: ToolMetadata) -> str:
    category = metadata.category
    return category if category != "unknown" else "tool"


def _infer_task_category(tool_name: str, domain: str) -> str:
    if tool_name == "run_shell_command":
        return "command_execution"
    return f"{domain}_tool_call"


def _infer_task_relevant_tools(tool_name: str, available_tools: list[str]) -> list[str]:
    if tool_name in available_tools:
        return [tool_name]
    return available_tools


def _infer_intent_forbidden_tools(
    tool_name: str,
    available_tools: list[str],
    raw_user_request: str,
) -> list[str]:
    if tool_name not in GMAIL_SEND_TOOL_NAMES:
        return []
    request = raw_user_request.lower()
    negative_phrases = [
        "do not send",
        "don't send",
        "dont send",
        "not send",
        "without sending",
        "draft only",
        "only draft",
    ]
    if not any(phrase in request for phrase in negative_phrases):
        return []
    return [tool for tool in available_tools if tool in GMAIL_SEND_TOOL_NAMES] or [tool_name]


def _confirmation_required_tools(tool_name: str, metadata: ToolMetadata) -> list[str]:
    if metadata.requires_confirmation_by_default:
        return [tool_name]
    return []


def _execution_status(response: Any) -> str:
    if isinstance(response, Mapping):
        if response.get("blocked_by_agentguard"):
            return "blocked"
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
        if response.get("blocked_by_agentguard"):
            pieces.append("blocked_by_agentguard=true")
        if response.get("error"):
            pieces.append(f"error={str(response.get('error'))[:max_chars]}")
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


def adk_runtime_policy(guard_decision: str) -> str:
    if guard_decision in {"allow", "warn"}:
        return "allow"
    if guard_decision == "block":
        return "block"
    return "require_approval"


def _decision_from_v2(
    result: FirewallResultV1,
    evaluation: FirewallV2Evaluation,
):
    recommendation = evaluation.recommendation
    if recommendation not in {"allow", "require_approval", "block"}:
        recommendation = "block"
    policy = evaluation.policy_evaluation or {}
    matched_rules = policy.get("matched_rules") or []
    rule_ids = [
        str(rule.get("rule_id"))
        for rule in matched_rules
        if isinstance(rule, dict) and rule.get("rule_id")
    ]
    if not rule_ids:
        rule_ids = [
            f"firewall_v2_default:{recommendation}",
        ]
    score_by_decision = {
        "allow": 0.05,
        "require_approval": 0.72,
        "block": 0.95,
    }
    return result.decision.model_copy(
        update={
            "decision": recommendation,
            "tier_used": "static_policy",
            "final_risk_score": score_by_decision[recommendation],
            "decision_rules_fired": rule_ids,
            "explanation": (
                f"FirewallV2 enforced {recommendation}. "
                f"{policy.get('explanation') or evaluation.explanation}"
            ),
        }
    )


def _runtime_event_payload(
    result: FirewallResultV1,
    execution_status: str,
    output_summary: str,
) -> dict[str, Any]:
    runtime_policy = adk_runtime_policy(result.decision.decision)
    return {
        "runtime_event_source": "google_adk_adapter",
        "call_id": result.trace.proposed_tool_call.call_id,
        "execution_status": execution_status,
        "output_summary": output_summary,
        "runtime_policy": runtime_policy,
        "approval_required": runtime_policy == "require_approval",
        "firewall_decision": result.decision.decision,
        "decision_id": result.decision.decision_id,
        "score_id": result.score.score_id,
    }
