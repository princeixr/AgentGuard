# Google ADK Personal Agent

This is an independent chatbot application. It owns Google ADK, chat, tools, MCP configuration, and tool execution. It talks to AgentGuard only through the public `agentguard-sdk` HTTP client.

## Runtime Flow

```text
User chat
  -> Google ADK model proposes tool call
  -> before_tool_callback sends ToolProposal to AgentGuard
  -> allow: ADK executes original tool
  -> require_approval: wait for AgentGuard UI approval
  -> block/reject/timeout: tool is not executed
  -> after_tool_callback reports OutcomeReport
```

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -e ../agentguard-product/packages/agentguard-sdk
.venv/bin/pip install -e .
cp .env.example .env
```

Set `AGENTGUARD_BASE_URL`, `AGENTGUARD_API_KEY`, and `GOOGLE_API_KEY`.

## Run

```bash
.venv/bin/adk web
```

Open the ADK web UI and select the personal agent. Keep the AgentGuard product API running separately.
