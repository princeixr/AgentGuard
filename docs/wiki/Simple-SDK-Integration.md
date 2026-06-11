# Simple SDK Integration

The high-level Python SDK is the easiest way to add AgentGuard to an existing chatbot.

## Install

```bash
pip install agentguard-sdk
```

Local development from this repo:

```bash
pip install -e agentguard-product/packages/agentguard-sdk
```

## One-Call Guard Check

Use `AgentGuard.check(...)` immediately before executing a tool.

```python
import os

from agentguard_sdk import AgentGuard

guard = AgentGuard(
    agent_id="customer_support_bot",
    base_url=os.environ["AGENTGUARD_BASE_URL"],
    api_key=os.environ["AGENTGUARD_API_KEY"],
    environment="production",
)

decision = guard.check(
    user_message="Send Rahul the project update.",
    tool="send_email",
    args={
        "to": "rahul@example.com",
        "subject": "Project update",
        "body": "Here is the update...",
    },
    tool_type="email.send",
)

if decision.allowed:
    send_email(
        to="rahul@example.com",
        subject="Project update",
        body="Here is the update...",
    )
else:
    print(decision.reason)
```

## Approval-Aware Execution

If you want your agent process to wait until an operator resolves approval:

```python
decision = guard.check(
    user_message=user_message,
    tool="send_email",
    args=email_args,
    tool_type="email.send",
    approval_mode="wait",
)

if decision.allowed:
    send_email(**email_args)
else:
    return f"AgentGuard stopped this action: {decision.reason}"
```

## Decorator Style

Decorators are useful when your tools are plain Python functions.

```python
from agentguard_sdk import AgentGuard

guard = AgentGuard(agent_id="ops_assistant")


@guard.tool(tool_type="shell.command")
def run_command(command: str) -> str:
    """Run a shell command on the server."""
    return subprocess.check_output(command, shell=True, text=True)


output = run_command(
    command="ls -la",
    user_message="Show me the files in this directory.",
)
```

The decorator:

1. Registers tool metadata.
2. Checks the tool call with AgentGuard.
3. Waits for approval when needed.
4. Blocks execution if AgentGuard denies the call.
5. Reports the execution outcome.

## What AgentGuard Returns

| Field | Meaning |
|---|---|
| `decision` | `allow`, `require_approval`, or `block` |
| `allowed` | Convenience boolean for execution |
| `requires_approval` | Whether an operator approval is pending |
| `reason` | Human-readable explanation |
| `approval_id` | Approval request ID when applicable |
| `trace_id` | Audit trace ID |
| `decision_id` | Decision ID used for outcome reporting |
| `tier_evidence` | Evidence from deterministic and LLM evaluations |

## Best Practices

- Call AgentGuard **immediately before** tool execution.
- Do not let the model override AgentGuard decisions.
- Use stable `agent_id`, `workspace_id`, and `deployment_id` values.
- Use specific `tool_type` values like `email.send`, `file.delete`, or `payment.send`.
- Report outcomes after execution, failure, blocking, or cancellation.

