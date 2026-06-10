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

## MCP Server Configuration

Two MCP servers are configured in `config/adk_mcp_servers.toml`:

### Gmail MCP (Docker)

The Gmail server runs as a Docker container with OAuth credentials mounted from a volume.
Follow the setup in `external/Gmail-MCP-Server/README.md` to build the image and populate the
`mcp-gmail` volume with `gcp-oauth.keys.json` and `credentials.json`.

### Google Workspace MCP (Calendar, Gmail via Workspace)

The workspace server (`gemini-workspace-server`) uses Google's own OAuth client to access
Calendar and Gmail. It requires a one-time browser-based login to cache credentials locally.
Because the server runs as a headless stdio subprocess it cannot open a browser itself, so
the login must be done separately before starting the agent.

Run the headless login once before starting the agent. Use the same `npx` specifier that
the agent uses so the token lands in the same cache directory:

```bash
npx --package=github:gemini-cli-extensions/workspace#v0.0.8 gemini-workspace-server login
```

The command prints an auth URL. Open it in your browser, complete the Google OAuth flow
(grant Calendar, Gmail, and Drive scopes), then return to the terminal. The token is saved
in the npx cache and reused on every subsequent start — `config/adk_mcp_servers.toml`
needs no changes.

> **Re-authentication**: tokens expire periodically. If Calendar calls start timing out again,
> re-run the login command above.

## Run

```bash
.venv/bin/adk web
```

Open the ADK web UI and select the personal agent. Keep the AgentGuard product API running separately.
