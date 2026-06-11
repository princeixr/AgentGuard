# Tool Registry

AgentGuard needs to understand what a tool does before it can reason about risk. The tool registry provides standardized metadata for common tool classes.

## Built-In Tool Types

| Tool type | Typical risk | Example |
|---|---:|---|
| `email.send` | High | Send an external email |
| `email.draft` | Medium | Create a draft but do not send |
| `web.search` | Low/Medium | Search public web |
| `file.read` | Medium | Read local or cloud files |
| `file.write` | Medium/High | Modify a file |
| `file.delete` | High | Delete data |
| `calendar.create` | Medium | Create or update meetings |
| `payment.send` | Critical | Move money |
| `shell.command` | Critical | Execute shell commands |

Unknown tools default to conservative metadata so AgentGuard does not under-estimate risk.

## Explicit Registration

```python
guard.register_tool(
    "send_email",
    tool_type="email.send",
    description="Send an email to one or more recipients.",
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to", "subject", "body"],
    },
)
```

## Metadata Overrides

Use overrides when your tool has organization-specific behavior.

```python
decision = guard.check(
    user_message=user_message,
    tool="internal_refund",
    args={"customer_id": "cus_123", "amount": 25},
    tool_type="payment.send",
    metadata_overrides={
        "risk_level": "critical",
        "domain": "billing",
        "operation": "refund",
        "capabilities": ["billing.refund"],
    },
)
```

## Recommended Naming

Use names that describe the real side effect:

- Prefer `send_email` over `gmail_tool`.
- Prefer `delete_file` over `file_tool`.
- Prefer `create_calendar_event` over `calendar`.
- Prefer `run_shell_command` over `execute`.

Good names improve metadata inference and make approval screens easier for operators.

## Registry Design Principle

Tool metadata is not only documentation. It directly affects:

- policy matching
- risk tier routing
- approval UI clarity
- audit trace quality
- LLM judge context
- future analytics

Treat tool metadata like an API contract.

