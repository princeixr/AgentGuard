# API Reference

AgentGuard exposes two API layers:

- **V2 simple guard API** for normal users.
- **V1 low-level runtime API** for framework adapter authors.

All protected API calls use:

```http
Authorization: Bearer <AGENTGUARD_API_KEY>
```

## V2: One-Call Guard Check

```http
POST /api/v2/guard/check
```

Example:

```json
{
  "agent_id": "my_chatbot",
  "user_message": "Send Rahul the project update.",
  "tool_name": "send_email",
  "tool_type": "email.send",
  "arguments": {
    "to": "rahul@example.com",
    "subject": "Project update",
    "body": "Here is the update..."
  },
  "approval_mode": "async"
}
```

Response:

```json
{
  "allowed": false,
  "requires_approval": true,
  "decision": "require_approval",
  "reason": "Email send requires approval.",
  "approval_id": "appr_...",
  "trace_id": "trace_...",
  "decision_id": "dec_...",
  "tool_type": "email.send",
  "risk_level": "high_risk"
}
```

## Approval APIs

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/approvals` | List pending/resolved approvals |
| `POST /api/v1/approvals/{approval_id}/approve` | Approve a request |
| `POST /api/v1/approvals/{approval_id}/reject` | Reject a request |

## Low-Level Runtime APIs

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/agents/register` | Register agent and tools |
| `POST /api/v1/turns/start` | Start a user turn and create intent context |
| `POST /api/v1/tool-proposals/evaluate` | Evaluate a proposed tool call |
| `POST /api/v1/tool-outcomes` | Report executed/blocked/failed/cancelled outcome |
| `GET /api/v1/events/stream` | Live SSE events for dashboard/runtime |

## Decision Semantics

| Decision | Caller behavior |
|---|---|
| `allow` | Execute the tool |
| `require_approval` | Wait for approval or return pending state |
| `block` | Do not execute the tool |

## Idempotency

AgentGuard caches repeated tool proposals for a configurable TTL. Use stable `call_id` values when retrying the same tool proposal.

