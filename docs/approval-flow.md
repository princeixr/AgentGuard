# Approval Flow

AgentGuard uses HTTP for decisions and SSE for dashboard updates.

```text
ToolProposal
  -> AgentGuard evaluates the proposal
  -> decision=require_approval
  -> PendingApproval is stored
  -> SSE event approval.pending updates dashboard
  -> operator clicks Approve/Reject
  -> HTTP POST resolves approval
  -> SSE event approval.resolved updates dashboard
  -> SDK polling sees approved/rejected
  -> agent executes or blocks the original tool call
```

The approval UI shows user intent, tool arguments, deterministic policy evidence, LLM judge evidence, combiner owner, and final explanation.
