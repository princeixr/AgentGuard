"""Shared builder for canonical AgentGuardTraceV1 records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agentguard.core.models import ExecutedToolCall, RawTraceRecord, ScenarioRecord
from agentguard.runtime.tool_event_mapper import (
    infer_tool_category,
    infer_tool_risk_level,
    summarize_arguments,
)
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    ExecutionStateV1,
    ExplicitConstraintV1,
    IntentContractV1,
    RetrievalTextV1,
    ToolCallV1,
    ToolOutputContextV1,
    TraceSourceV1,
    TrajectoryV1,
)

@dataclass(frozen=True)
class TraceV1BuildInput:
    session_id: str
    step_index: int
    source: TraceSourceV1
    raw_user_request: str
    normalized_intent: str
    domain: str
    task_category: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None
    previous_trace_id: str | None = None
    available_tools: list[str] = field(default_factory=list)
    task_relevant_tools: list[str] = field(default_factory=list)
    intent_forbidden_tools: list[str] = field(default_factory=list)
    confirmation_required_tools: list[str] = field(default_factory=list)
    explicit_constraints: list[ExplicitConstraintV1] = field(default_factory=list)
    allowed_data_scopes: list[str] = field(default_factory=list)
    forbidden_data_scopes: list[str] = field(default_factory=list)
    prior_tool_calls: list[ExecutedToolCall] = field(default_factory=list)
    previous_output_summary: str | None = None
    contains_untrusted_instruction: bool = False
    contains_external_link: bool = False
    contains_secret_like_content: bool = False
    output_influenced_current_call: bool = False
    execution_status: str = "proposed"
    mcp_server: str | None = None
    tool_category: str | None = None
    risk_level: str | None = None
    side_effect_type: str | None = None


class TraceV1Builder:
    def build(self, data: TraceV1BuildInput) -> AgentGuardTraceV1:
        tool_category = data.tool_category or infer_tool_category(data.tool_name)
        inferred_risk = infer_tool_risk_level(data.tool_name)
        risk_level = data.risk_level or (
            inferred_risk.value if hasattr(inferred_risk, "value") else str(inferred_risk)
        )
        argument_summary = summarize_arguments(data.arguments)
        trajectory = build_trajectory(data.prior_tool_calls, data.previous_output_summary)
        explicit_constraints = data.explicit_constraints or constraints_from_intent(
            raw_request=data.raw_user_request,
            forbidden_tools=data.intent_forbidden_tools,
        )
        intent = IntentContractV1(
            raw_user_request=data.raw_user_request,
            normalized_intent=data.normalized_intent,
            task_goal=infer_task_goal(data.domain, data.task_category),
            domain=data.domain,
            task_category=data.task_category,
            available_tools=data.available_tools,
            task_relevant_tools=data.task_relevant_tools,
            intent_forbidden_tools=data.intent_forbidden_tools,
            confirmation_required_tools=data.confirmation_required_tools,
            explicit_constraints=explicit_constraints,
            allowed_data_scopes=data.allowed_data_scopes,
            forbidden_data_scopes=data.forbidden_data_scopes,
        )
        proposed_call = ToolCallV1(
            call_id=data.call_id or str(uuid4()),
            tool_name=data.tool_name,
            tool_category=tool_category,
            mcp_server=data.mcp_server,
            risk_level=risk_level,
            side_effect_type=data.side_effect_type or infer_side_effect_type(data.tool_name),
            arguments=data.arguments,
            argument_summary=argument_summary,
            argument_hash=hash_arguments(data.arguments),
        )
        return AgentGuardTraceV1(
            trace_id=str(uuid4()),
            session_id=data.session_id,
            previous_trace_id=data.previous_trace_id,
            step_index=data.step_index,
            source=data.source,
            intent=intent,
            proposed_tool_call=proposed_call,
            trajectory=trajectory,
            tool_output_context=ToolOutputContextV1(
                contains_untrusted_instruction=data.contains_untrusted_instruction,
                contains_external_link=data.contains_external_link,
                contains_secret_like_content=data.contains_secret_like_content,
                output_influenced_current_call=data.output_influenced_current_call,
            ),
            retrieval_text=build_retrieval_text(
                normalized_intent=data.normalized_intent,
                trajectory=trajectory,
                tool_name=data.tool_name,
                argument_summary=argument_summary,
            ),
            execution=ExecutionStateV1(status=data.execution_status),
        )

    def from_raw_trace(
        self,
        trace: RawTraceRecord,
        source_mode: str = "historical",
        agent_config_id: str | None = None,
        scenario_id: str | None = None,
        run_id: str | None = None,
        available_tools: list[str] | None = None,
    ) -> AgentGuardTraceV1:
        prior = trace.prior_tool_calls
        previous_output = prior[-1].output_summary if prior else None
        constraints = constraints_from_intent(
            raw_request=trace.user_intent.raw_request,
            forbidden_tools=trace.user_intent.disallowed_tools,
        )
        return self.build(
            TraceV1BuildInput(
                session_id=trace.session_id,
                step_index=trace.step_index,
                source=TraceSourceV1(
                    mode=source_mode,
                    agent_framework=trace.agent_framework,
                    source_type=trace.source_type,
                    agent_id=trace.agent_id,
                    agent_config_id=agent_config_id,
                    scenario_id=scenario_id,
                    run_id=run_id,
                ),
                raw_user_request=trace.user_intent.raw_request,
                normalized_intent=trace.user_intent.normalized_intent,
                domain=trace.domain,
                task_category=trace.task_category,
                tool_name=trace.proposed_tool_call.tool_name,
                arguments=trace.proposed_tool_call.arguments,
                call_id=trace.proposed_tool_call.call_id,
                available_tools=available_tools or sorted(
                    set(trace.user_intent.allowed_tools + trace.user_intent.disallowed_tools)
                ),
                task_relevant_tools=trace.user_intent.allowed_tools,
                intent_forbidden_tools=trace.user_intent.disallowed_tools,
                confirmation_required_tools=trace.user_intent.requires_confirmation_for,
                explicit_constraints=constraints,
                prior_tool_calls=prior,
                previous_output_summary=previous_output,
                contains_untrusted_instruction=trace.tool_output_context.contains_untrusted_instruction,
                contains_external_link=trace.tool_output_context.contains_external_link,
                contains_secret_like_content=trace.tool_output_context.contains_secret_like_content,
                output_influenced_current_call=trace.tool_output_context.output_influenced_current_call,
                execution_status=trace.execution_status,
            )
        )


def build_trajectory(
    prior_tool_calls: list[ExecutedToolCall],
    previous_output_summary: str | None = None,
) -> TrajectoryV1:
    names = [call.tool_name for call in prior_tool_calls]
    previous_call = prior_tool_calls[-1] if prior_tool_calls else None
    side_effect_count = sum(1 for call in prior_tool_calls if infer_side_effect_type(call.tool_name))
    blocked_count = sum(1 for call in prior_tool_calls if call.status == "blocked")
    return TrajectoryV1(
        prior_tool_names=names,
        prior_tool_sequence=" -> ".join(names),
        prior_tool_count=len(prior_tool_calls),
        previous_tool_name=previous_call.tool_name if previous_call else None,
        previous_output_summary=previous_output_summary,
        prior_side_effect_count=side_effect_count,
        prior_blocked_count=blocked_count,
        prior_approval_required_count=0,
    )


def build_retrieval_text(
    normalized_intent: str,
    trajectory: TrajectoryV1,
    tool_name: str,
    argument_summary: str,
) -> RetrievalTextV1:
    sequence = trajectory.prior_tool_sequence
    trajectory_text = f"{sequence} -> {tool_name}" if sequence else tool_name
    summary = (
        f"Intent: {normalized_intent}. Prior tools: {sequence or 'none'}. "
        f"Proposed tool: {tool_name}. Arguments: {argument_summary}."
    )
    return RetrievalTextV1(
        summary=summary,
        intent_text=normalized_intent,
        trajectory_text=trajectory_text,
        argument_text=argument_summary,
    )


def hash_arguments(arguments: dict[str, Any]) -> str | None:
    if not arguments:
        return None
    encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def infer_task_goal(domain: str, task_category: str) -> str:
    return f"{domain}_{task_category}".strip("_")


def infer_side_effect_type(tool_name: str) -> str | None:
    if tool_name == "run_shell_command":
        return "shell_command"
    if tool_name == "calendar_create_event":
        return "calendar_event_create"
    if tool_name == "calendar_update_event":
        return "calendar_event_update"
    if tool_name == "file_write":
        return "file_write"
    if tool_name == "file_delete":
        return "file_delete"
    return None


def constraints_from_scenario(scenario: ScenarioRecord) -> list[ExplicitConstraintV1]:
    return constraints_from_intent(
        raw_request=scenario.user_request,
        forbidden_tools=scenario.expected_disallowed_tools,
    )


def constraints_from_intent(
    raw_request: str,
    forbidden_tools: list[str],
) -> list[ExplicitConstraintV1]:
    request = raw_request.lower()
    constraints: list[ExplicitConstraintV1] = []
    if "do not send" in request or "don't send" in request:
        constraints.append(
            ExplicitConstraintV1(
                constraint_type="negative_action",
                text="Do not send.",
                forbidden_tool=next(
                    (tool for tool in forbidden_tools if "send" in tool.lower()),
                    None,
                ),
            )
        )
    if "do not create" in request or "don't create" in request:
        forbidden_tool = next((tool for tool in forbidden_tools if "create" in tool), None)
        constraints.append(
            ExplicitConstraintV1(
                constraint_type="negative_action",
                text="Do not create.",
                forbidden_tool=forbidden_tool,
            )
        )
    if "only" in request:
        constraints.append(
            ExplicitConstraintV1(
                constraint_type="scope_limit",
                text="User constrained the task scope with 'only'.",
            )
        )
    return constraints
