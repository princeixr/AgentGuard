"""Hackathon demo entrypoint placeholder."""

from agentguard.governance.guard_engine import GuardEngine
from agentguard.runtime.interceptor import ToolInterceptor
from agentguard.runtime.mock_runtime import MockRuntimeAdapter
from agentguard.tracing.trace_builder import TraceBuilder
from agentguard.tracing.trace_store import TraceStore


def main() -> None:
    runtime = MockRuntimeAdapter(
        interceptor=ToolInterceptor(GuardEngine()),
        trace_builder=TraceBuilder(),
        trace_store=TraceStore(),
    )
    traces = runtime.run_session("email_draft_not_send_001")
    print(f"Generated {len(traces)} demo trace(s).")


if __name__ == "__main__":
    main()

