from agentguard.evaluation.dataset_models import BenchmarkTraceRecord, TraceSourceProvenance
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    ExecutionStateV1,
    IntentContractV1,
    RetrievalTextV1,
    ToolCallV1,
    TraceSourceV1,
    TrajectoryV1,
)


def test_benchmark_trace_record_wraps_v1_trace_with_provenance():
    trace = AgentGuardTraceV1(
        trace_id="trace_001",
        session_id="session_001",
        step_index=1,
        source=TraceSourceV1(
            mode="historical",
            agent_framework="openclaw",
            source_type="live_openclaw",
            agent_id="openclaw_file_agent",
            scenario_id="scenario_001",
        ),
        intent=IntentContractV1(
            raw_user_request="Inspect a file.",
            normalized_intent="Inspect a file.",
            domain="file",
            task_category="file_inspection",
            available_tools=["read"],
            task_relevant_tools=["read"],
        ),
        proposed_tool_call=ToolCallV1(
            call_id="call_001",
            tool_name="read",
            tool_category="file",
            risk_level="read_only",
            arguments={"path": "/workspace/README.md"},
            argument_summary="path=/workspace/README.md",
            argument_hash="sha256:test",
        ),
        trajectory=TrajectoryV1(),
        retrieval_text=RetrievalTextV1(
            summary="Inspect a file with read.",
            intent_text="Inspect a file.",
            trajectory_text="read",
            argument_text="path=/workspace/README.md",
        ),
        execution=ExecutionStateV1(status="proposed"),
    )
    record = BenchmarkTraceRecord(
        trace=trace,
        provenance=TraceSourceProvenance(
            source_framework="openclaw",
            source_type="live_openclaw",
            source_session_id="session_001",
            source_tool_call_id="call_001",
            source_transcript_path="data/openclaw_raw/transcripts/session_001.jsonl",
            scenario_id="scenario_001",
        ),
    )

    assert record.trace.schema_version == "agentguard.trace.v1"
    assert record.provenance.source_framework == "openclaw"
