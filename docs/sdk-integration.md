# SDK Integration

Install:

```bash
pip install agentguard-sdk
```

## Recommended: One-Call Check

For most custom chatbots, use the high-level SDK. AgentGuard auto-registers the
tool, starts a turn, evaluates the proposed call, and returns a simple decision.

```python
import os

from agentguard_sdk import AgentGuard

guard = AgentGuard(
    agent_id="my_chatbot",
    base_url="http://localhost:8000",
    api_key=os.environ["AGENTGUARD_API_KEY"],
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
    send_email(...)
else:
    print(decision.reason)
```

If you want AgentGuard to block until the approval UI resolves the request:

```python
decision = guard.check(
    user_message=user_message,
    tool="send_email",
    args=email_args,
    approval_mode="wait",
)
```

## Python Decorator

```python
from agentguard_sdk import AgentGuard

guard = AgentGuard(agent_id="my_chatbot")

@guard.tool(tool_type="email.send")
def send_email(to: str, subject: str, body: str):
    ...

send_email(
    to="rahul@example.com",
    subject="Update",
    body="Hello",
    user_message="Send Rahul the update.",
)
```

## Advanced: Low-Level Flow

```python
import os

from agentguard_sdk import HttpAgentGuardClient, ToolProposal

client = HttpAgentGuardClient(
    base_url="http://localhost:8000",
    api_key=os.environ["AGENTGUARD_API_KEY"],
)

decision = client.evaluate(ToolProposal(...))

if decision.decision == "allow":
    run_tool()
elif decision.decision == "require_approval":
    approval = client.wait_for_approval(decision.approval_request_id)
    if approval.status == "approved":
        run_tool()
else:
    block_tool()
```

See `examples/minimal-python-agent/` for a complete runnable integration.
