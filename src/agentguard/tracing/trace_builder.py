"""Builds raw trace records from runtime state."""

from uuid import uuid4

from agentguard.core.models import (
    ExecutedToolCall,
    ProposedToolCall,
    RawTraceRecord,
    ToolOutputContext,
    UserIntent,
)


class TraceBuilder:
    def build(
        self,
        agent_id: str,
        agent_framework: str,
        domain: str,
        task_category: str,
        user_intent: UserIntent,
        proposed_tool_call: ProposedToolCall,
        prior_tool_calls: list[ExecutedToolCall] | None = None,
        tool_output_context: ToolOutputContext | None = None,
        execution_status: str = "proposed",
        source_type: str = "live",
    ) -> RawTraceRecord:
        return RawTraceRecord(
            trace_id=str(uuid4()),
            session_id=user_intent.session_id,
            agent_id=agent_id,
            agent_framework=agent_framework,
            domain=domain,
            task_category=task_category,
            user_intent=user_intent,
            step_index=proposed_tool_call.step_index,
            proposed_tool_call=proposed_tool_call,
            prior_tool_calls=prior_tool_calls or [],
            tool_output_context=tool_output_context or ToolOutputContext(),
            execution_status=execution_status,
            source_type=source_type,
        )

