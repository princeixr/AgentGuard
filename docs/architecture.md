# Architecture

AgentGuard is an approval and runtime-governance layer for tool-using agents.

```text
Agent / chatbot runtime
  -> AgentGuard SDK
  -> AgentGuard API
  -> AgentGuard firewall
       -> intent extraction
       -> tool descriptor
       -> action normalization
       -> deterministic policy + security checks
       -> LLM judge
       -> deterministic combiner
  -> allow | require_approval | block
  -> approval UI if needed
  -> outcome report
```

## Components

- **AgentGuard API**: FastAPI service exposing registration, turn, proposal, approval, outcome, and SSE endpoints.
- **AgentGuard SDK**: Lightweight client used by agent frameworks.
- **AgentGuard Dashboard**: React UI for agents, live events, approvals, decision memory, and operations.
- **AgentGuard Firewall**: Production decision engine. The live remote path always runs deterministic checks and an LLM judge, combining results conservatively.
- **Approval queue**: Stores pending approval records and streams updates via SSE.

## Communication

- Agent to AgentGuard: HTTP request/response.
- AgentGuard UI live updates: SSE.
- Agent approval waiting: SDK polling.
