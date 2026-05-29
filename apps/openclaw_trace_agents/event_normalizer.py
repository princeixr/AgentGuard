"""Normalize OpenClaw tool events into AgentGuard raw traces.

This module is for dataset construction only. It does not call AgentGuard governance
and it does not enforce decisions against OpenClaw.
"""

from __future__ import annotations

from agentguard.core.models import (
    ExecutedToolCall,
    RawTraceRecord,
    ScenarioRecord,
    ToolOutputContext,
    UserIntent,
)
from agentguard.runtime.tool_event_mapper import map_openclaw_tool_event_to_proposed_call
from agentguard.tracing.trace_builder import TraceBuilder
from apps.openclaw_trace_agents.base import OpenClawToolEvent


class OpenClawEventNormalizer:
    def __init__(self, trace_builder: TraceBuilder | None = None, source_type: str = "live_openclaw"):
        self.trace_builder = trace_builder or TraceBuilder()
        self.source_type = source_type

    def normalize_events(
        self,
        agent_id: str,
        domain: str,
        scenario: ScenarioRecord,
        events: list[OpenClawToolEvent],
        max_steps: int = 20,
        system_prompt_hash: str | None = None,
        tool_schema_snapshot_id: str | None = None,
        session_id: str | None = None,
    ) -> list[RawTraceRecord]:
        user_intent = self._build_user_intent(scenario, session_id=session_id)
        prior_tool_calls: list[ExecutedToolCall] = []
        traces: list[RawTraceRecord] = []
        previous_output: str | None = None
        previous_untrusted = False
        previous_external_link = False
        previous_secret_like = False
        previous_influenced_next = False

        for step_index, event in enumerate(events[:max_steps], start=1):
            proposed_call = map_openclaw_tool_event_to_proposed_call(
                event,
                session_id=user_intent.session_id,
                step_index=step_index,
            )
            trace = self.trace_builder.build(
                agent_id=agent_id,
                agent_framework="openclaw",
                domain=domain,
                task_category=scenario.task_category,
                user_intent=user_intent,
                proposed_tool_call=proposed_call,
                prior_tool_calls=list(prior_tool_calls),
                tool_output_context=ToolOutputContext(
                    immediate_prior_output_summary=previous_output,
                    contains_untrusted_instruction=previous_untrusted,
                    contains_external_link=previous_external_link,
                    contains_secret_like_content=previous_secret_like,
                    output_influenced_current_call=previous_influenced_next,
                ),
                execution_status="proposed",
                source_type=self.source_type,
                system_prompt_hash=system_prompt_hash,
                tool_schema_snapshot_id=tool_schema_snapshot_id,
            )
            traces.append(trace)
            prior_tool_calls.append(
                ExecutedToolCall(
                    call_id=proposed_call.call_id,
                    session_id=user_intent.session_id,
                    step_index=step_index,
                    tool_name=proposed_call.tool_name,
                    arguments=proposed_call.arguments,
                    output_summary=event.output_summary or "openclaw transcript did not include output",
                    status="executed",
                )
            )

            previous_output = event.output_summary
            previous_untrusted = event.contains_untrusted_instruction
            previous_external_link = event.contains_external_link
            previous_secret_like = event.contains_secret_like_content
            previous_influenced_next = event.output_influenced_next_call

        return traces

    def _build_user_intent(self, scenario: ScenarioRecord, session_id: str | None = None) -> UserIntent:
        return UserIntent(
            session_id=session_id or f"openclaw_{scenario.scenario_id}",
            raw_request=scenario.user_request,
            normalized_intent=scenario.user_request,
            allowed_domains=[scenario.domain],
            allowed_tools=scenario.expected_allowed_tools,
            disallowed_tools=scenario.expected_disallowed_tools,
            requires_confirmation_for=scenario.expected_disallowed_tools,
        )
