"""OpenClaw-specific adapter for canonical AgentGuardTraceV1 records."""

from __future__ import annotations

from agentguard.core.models import ExecutedToolCall, ScenarioRecord
from agentguard.tracing.schema_v1 import AgentGuardTraceV1, TraceSourceV1
from agentguard.tracing.trace_v1_builder import (
    TraceV1BuildInput,
    TraceV1Builder,
    constraints_from_scenario,
)


class OpenClawTraceV1Adapter:
    """Convert normalized OpenClaw tool events into canonical AgentGuard v1 traces."""

    def __init__(self, builder: TraceV1Builder | None = None):
        self.builder = builder or TraceV1Builder()

    def adapt_events(
        self,
        scenario: ScenarioRecord,
        events: list,
        session_id: str,
        agent_id: str,
        agent_config_id: str | None = None,
        run_id: str | None = None,
        environment_id: str | None = None,
        available_tools: list[str] | None = None,
        max_steps: int = 20,
    ) -> list[AgentGuardTraceV1]:
        prior_tool_calls: list[ExecutedToolCall] = []
        traces: list[AgentGuardTraceV1] = []
        previous_trace_id: str | None = None
        previous_output: str | None = None
        source = TraceSourceV1(
            mode="historical",
            agent_framework="openclaw",
            source_type="live_openclaw",
            agent_id=agent_id,
            agent_config_id=agent_config_id,
            scenario_id=scenario.scenario_id,
            run_id=run_id,
            environment_id=environment_id,
        )
        for step_index, event in enumerate(events[:max_steps], start=1):
            trace = self.builder.build(
                TraceV1BuildInput(
                    session_id=session_id,
                    step_index=step_index,
                    source=source,
                    raw_user_request=scenario.user_request,
                    normalized_intent=scenario.user_request,
                    domain=scenario.domain,
                    task_category=scenario.task_category,
                    tool_name=event.tool_name,
                    arguments=event.arguments,
                    call_id=event.source_tool_call_id,
                    previous_trace_id=previous_trace_id,
                    available_tools=available_tools
                    or sorted(
                        set(scenario.expected_allowed_tools + scenario.expected_disallowed_tools)
                    ),
                    task_relevant_tools=scenario.expected_allowed_tools,
                    intent_forbidden_tools=scenario.expected_disallowed_tools,
                    confirmation_required_tools=scenario.expected_disallowed_tools,
                    explicit_constraints=constraints_from_scenario(scenario),
                    prior_tool_calls=list(prior_tool_calls),
                    previous_output_summary=previous_output,
                    contains_untrusted_instruction=event.contains_untrusted_instruction,
                    contains_external_link=event.contains_external_link,
                    contains_secret_like_content=event.contains_secret_like_content,
                    output_influenced_current_call=event.output_influenced_next_call,
                    execution_status="proposed",
                )
            )
            traces.append(trace)
            previous_trace_id = trace.trace_id
            prior_tool_calls.append(
                ExecutedToolCall(
                    call_id=trace.proposed_tool_call.call_id,
                    session_id=session_id,
                    step_index=step_index,
                    tool_name=event.tool_name,
                    arguments=event.arguments,
                    output_summary=event.output_summary or "openclaw transcript did not include output",
                    status="executed",
                )
            )
            previous_output = event.output_summary
        return traces
