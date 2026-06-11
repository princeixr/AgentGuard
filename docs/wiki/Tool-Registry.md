# Tool Registry

AgentGuard includes built-in metadata for common tool classes:

- `email.send`
- `email.draft`
- `web.search`
- `file.read`
- `file.write`
- `file.delete`
- `calendar.create`
- `payment.send`
- `shell.command`

You can pass a tool type explicitly:

```python
guard.register_tool("send_email", tool_type="email.send")
```

Or rely on name inference:

```python
guard.check(user_message="Search docs", tool="web_search", args={"query": "AgentGuard"})
```

Unknown tools default to conservative high-risk metadata.
