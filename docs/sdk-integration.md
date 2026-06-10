# SDK Integration

Install:

```bash
pip install agentguard-sdk
```

Minimal flow:

```python
from agentguard_sdk import HttpAgentGuardClient, ToolProposal

client = HttpAgentGuardClient(
    base_url="http://localhost:8000",
    api_key="dev-agentguard-key",
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
