# Simple SDK Integration

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
    send_email(to="rahul@example.com", subject="Project update", body="Here is the update...")
else:
    print(decision.reason)
```

Use `approval_mode="wait"` if your app should pause until an operator approves
or rejects the tool call in the AgentGuard UI.
