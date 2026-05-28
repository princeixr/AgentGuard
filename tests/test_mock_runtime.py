from agentguard.governance.guard_engine import GuardEngine
from agentguard.runtime.interceptor import ToolInterceptor
from agentguard.runtime.mock_runtime import MockRuntimeAdapter
from agentguard.tracing.trace_builder import TraceBuilder
from agentguard.tracing.trace_store import TraceStore


def test_mock_runtime_returns_valid_raw_trace(tmp_path):
    runtime = MockRuntimeAdapter(
        interceptor=ToolInterceptor(GuardEngine()),
        trace_builder=TraceBuilder(),
        trace_store=TraceStore(root_dir=tmp_path),
    )

    traces = runtime.run_session("email_draft_not_send_001")

    assert len(traces) == 1
    assert traces[0].proposed_tool_call.tool_name == "gmail_send"
    assert (tmp_path / "raw" / "mock" / "traces.jsonl").exists()

