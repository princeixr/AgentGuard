from agentguard.core.enums import ToolRiskLevel
from agentguard.core.models import ProposedToolCall, RawTraceRecord, UserIntent
from agentguard.evaluation.dataset_models import BenchmarkTraceRecord, TraceSourceProvenance


def test_benchmark_trace_record_wraps_raw_trace_with_provenance():
    intent = UserIntent(
        session_id="session_001",
        raw_request="Inspect a file.",
        normalized_intent="Inspect a file.",
        allowed_domains=["file"],
        allowed_tools=["read"],
    )
    proposed = ProposedToolCall(
        call_id="call_001",
        session_id="session_001",
        step_index=1,
        tool_name="read",
        tool_category="file",
        risk_level=ToolRiskLevel.READ_ONLY,
        arguments={"path": "/workspace/README.md"},
        argument_summary="path=/workspace/README.md",
        argument_hash="sha256:test",
        proposed_by="openclaw_agent",
    )
    raw_trace = RawTraceRecord(
        trace_id="trace_001",
        session_id="session_001",
        agent_id="openclaw_file_agent",
        agent_framework="openclaw",
        domain="file",
        task_category="file_inspection",
        user_intent=intent,
        system_prompt_hash="sha256:system",
        tool_schema_snapshot_id="sha256:tools",
        step_index=1,
        proposed_tool_call=proposed,
        execution_status="proposed",
        source_type="live_openclaw",
    )
    record = BenchmarkTraceRecord(
        trace=raw_trace,
        provenance=TraceSourceProvenance(
            source_framework="openclaw",
            source_type="live_openclaw",
            source_session_id="session_001",
            source_tool_call_id="call_001",
            source_transcript_path="data/openclaw_raw/transcripts/session_001.jsonl",
            scenario_id="scenario_001",
        ),
    )

    assert record.trace.system_prompt_hash == "sha256:system"
    assert record.provenance.source_framework == "openclaw"
