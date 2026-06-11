# AgentGuard Wiki

AgentGuard is an open-source runtime governance layer for tool-using AI agents.
It intercepts proposed tool calls before execution, evaluates risk, requests
human approval when needed, and records trace evidence for auditability.

## Start Here

1. [Quickstart](Quickstart.md)
2. [Simple SDK Integration](Simple-SDK-Integration.md)
3. [Tool Registry](Tool-Registry.md)
4. [Approval Flow](Approval-Flow.md)
5. [Deployment](Deployment.md)

## Integration Options

- One-call REST API: `POST /api/v2/guard/check`
- Python SDK: `AgentGuard.check()`
- Python decorators: `@guard.tool(...)`
- Google ADK adapter: `protect_adk_agent(...)`
- Low-level V1 API for custom framework adapters
