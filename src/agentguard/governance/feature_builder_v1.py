"""Build TraceFeatureV1 records from canonical traces.

This first implementation uses deterministic local features. Elastic retrieval and
historical statistics can be plugged into the same output schema later.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from uuid import uuid4

from agentguard.runtime.tool_registry import ToolRegistry, build_default_tool_registry
from agentguard.tracing.schema_v1 import (
    ContextFeaturesV1,
    HistoricalStatisticsV1,
    PolicyFeaturesV1,
    RetrievalFeatureV1,
    TraceFeatureV1,
    AgentGuardTraceV1,
)


class TraceFeatureBuilderV1:
    def __init__(self, tool_registry: ToolRegistry | None = None):
        self.tool_registry = tool_registry or build_default_tool_registry()

    def build(self, trace: AgentGuardTraceV1) -> TraceFeatureV1:
        tool = trace.proposed_tool_call
        intent = trace.intent
        metadata = self.tool_registry.metadata(tool.tool_name)
        tool_args_text = " ".join(str(value) for value in tool.arguments.values())
        previous_output = trace.trajectory.previous_output_summary or ""
        tool_in_task_relevant_set = tool.tool_name in intent.task_relevant_tools
        tool_in_intent_forbidden_set = tool.tool_name in intent.intent_forbidden_tools
        explicit_constraint_violated = any(
            constraint.forbidden_tool == tool.tool_name
            for constraint in intent.explicit_constraints
            if constraint.forbidden_tool
        )
        data_scope_violation = any(scope in tool.argument_summary for scope in intent.forbidden_data_scopes)

        return TraceFeatureV1(
            feature_id=str(uuid4()),
            trace_id=trace.trace_id,
            session_id=trace.session_id,
            step_index=trace.step_index,
            retrieval=RetrievalFeatureV1(
                query_text=trace.retrieval_text.summary,
                top_k=0,
            ),
            historical_statistics=HistoricalStatisticsV1(
                sequence_percentile_rarity=0.2 if not tool_in_task_relevant_set else 0.0,
                argument_cluster_distance=0.3 if data_scope_violation else 0.0,
            ),
            policy_features=PolicyFeaturesV1(
                tool_in_task_relevant_set=tool_in_task_relevant_set,
                tool_in_intent_forbidden_set=tool_in_intent_forbidden_set,
                requires_confirmation=tool.tool_name in intent.confirmation_required_tools
                or metadata.requires_confirmation_by_default,
                explicit_constraint_violated=explicit_constraint_violated,
                domain_allowed=tool.tool_category == intent.domain,
                data_scope_violation=data_scope_violation,
                side_effect_present=metadata.side_effect_type is not None,
                irreversible_side_effect=metadata.irreversible,
            ),
            context_features=ContextFeaturesV1(
                untrusted_instruction_present=trace.tool_output_context.contains_untrusted_instruction,
                external_link_present=trace.tool_output_context.contains_external_link,
                secret_like_content_present=trace.tool_output_context.contains_secret_like_content,
                previous_output_to_tool_similarity=_text_similarity(previous_output, tool_args_text),
                intent_to_tool_similarity=_text_similarity(
                    intent.normalized_intent,
                    f"{tool.tool_name} {tool.argument_summary}",
                ),
            ),
        )


def _text_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()
