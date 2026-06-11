# Integration Guide

This page explains how to add AgentGuard to any tool-using chatbot.

## The Golden Rule

AgentGuard must run before the tool executes.

```python
decision = guard.check(...)

if decision.allowed:
    run_tool()
else:
    do_not_run_tool()
```

## Option A: One-Call SDK

Best for most Python apps.

```python
decision = guard.check(
    user_message=user_message,
    tool="send_email",
    args=email_args,
    tool_type="email.send",
)
```

The SDK automatically:

- registers the agent/tool if needed
- starts a turn
- evaluates the proposed tool call
- returns a decision
- includes approval metadata when needed

## Option B: REST API

Best for non-Python frameworks.

```bash
curl -X POST "$AGENTGUARD_BASE_URL/api/v2/guard/check" \
  -H "Authorization: Bearer $AGENTGUARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my_chatbot",
    "user_message": "Send Rahul the project update",
    "tool_name": "send_email",
    "tool_type": "email.send",
    "arguments": {
      "to": "rahul@example.com",
      "subject": "Project update",
      "body": "Here is the update..."
    }
  }'
```

## Option C: Low-Level Runtime API

Best for framework adapter authors.

1. `POST /api/v1/agents/register`
2. `POST /api/v1/turns/start`
3. `POST /api/v1/tool-proposals/evaluate`
4. wait for approval if needed
5. execute or block
6. `POST /api/v1/tool-outcomes`

Use this when your framework already has session, turn, and tool-call abstractions.

## Required Integration Points

| Point | Required? | Why |
|---|---:|---|
| Agent ID | Yes | Stable identity in dashboard and audit records |
| User message | Yes | Used for intent alignment |
| Tool name | Yes | Identifies the action |
| Tool arguments | Yes | Evaluates scope and risk |
| Tool type | Strongly recommended | Improves risk classification |
| Outcome report | Recommended | Completes audit trail |

## Enforcement Pattern

```python
def guarded_tool_call(user_message, tool_name, args):
    decision = guard.check(
        user_message=user_message,
        tool=tool_name,
        args=args,
        approval_mode="wait",
    )

    if not decision.allowed:
        return {"status": "blocked", "reason": decision.reason}

    try:
        result = execute_tool(tool_name, args)
        guard.client.report_outcome(...)
        return result
    except Exception:
        guard.client.report_outcome(...)
        raise
```

## Integration Checklist

- Intercept every tool call.
- Never execute on `block`.
- Never execute on unresolved `require_approval`.
- Preserve stable `session_id`, `turn_id`, and `call_id` when possible.
- Register tools with accurate metadata.
- Send outcome reports.
- Fail closed if AgentGuard is unreachable for high-risk tools.

