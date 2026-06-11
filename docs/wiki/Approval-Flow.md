# Approval Flow

```text
Tool call proposed
  ↓
AgentGuard evaluates policy and tiers
  ↓
Decision
  ├─ allow → chatbot executes tool
  ├─ require_approval → operator approves/rejects in UI
  └─ block → chatbot does not execute tool
  ↓
Chatbot reports outcome
```

The approval UI listens to AgentGuard SSE events and uses the API to approve or
reject pending calls.
