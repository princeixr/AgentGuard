# Tool Registry

AgentGuard ships with a built-in tool registry so new users do not need to
manually write governance metadata for common tools.

## Built-In Types

- `email.send`
- `email.draft`
- `web.search`
- `file.read`
- `file.write`
- `file.delete`
- `calendar.create`
- `payment.send`
- `shell.command`

Each type maps to domain, operation, capability, side-effect, reversibility, and
risk metadata used by the firewall.

## SDK Usage

```python
guard.register_tool("send_email", tool_type="email.send")
```

Or let AgentGuard infer from the name:

```python
guard.check(
    user_message="Send Rahul the update.",
    tool="send_email",
    args={"to": "rahul@example.com"},
)
```

Unknown tools are treated conservatively as high-risk custom tools.

## Overrides

Use overrides when your deployment has stricter requirements:

```python
guard.register_tool(
    "send_invoice_email",
    tool_type="email.send",
    metadata_overrides={
        "risk_level": "critical_risk",
        "requires_approval_default": True,
    },
)
```

The low-level V1 API still accepts full `ToolManifest` objects for teams that
want complete control.
