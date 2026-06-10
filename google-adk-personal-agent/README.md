# Google ADK Personal Agent

This is an independent agent application. It owns Google ADK, model credentials, MCP
connections, tools, execution, and the future personal-agent UI.

It depends only on the public `agentguard-sdk` package. It does not import AgentGuard
firewall, policy, tracing, storage, control-plane, dashboard, or server modules.

The current development mode uses `FakeAgentGuardClient` so both projects can be tested
before HTTP transport is implemented.

```bash
python -m venv .venv
.venv/bin/pip install -e ../agentguard-product/packages/agentguard-sdk
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/python -m personal_agent.chat
```

The process registers a sanitized manifest through the SDK client. MCP connection
commands, headers, URLs, environment values, and credentials remain inside this
repository and are never included in the manifest.
