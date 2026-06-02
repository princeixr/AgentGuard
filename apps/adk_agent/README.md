# ADK Terminal Assistant

A minimal conversational [Google ADK](https://google.github.io/adk-docs/) agent
you can chat with. It has one local tool, `run_shell_command`, and can
optionally expose a Docker-backed Gmail MCP server.

## Files

- `agent.py` — defines the `run_shell_command` tool and the `root_agent`.
- `chat.py` — a standalone interactive chat loop (no extra CLI needed).
- `__init__.py` — makes the package discoverable by `adk run` / `adk web`.

## Setup

```bash
uv sync                         # installs deps, incl. google-adk (or: pip install -e .)
cp .env.example .env
# edit .env and set GOOGLE_API_KEY=...
```

Get a Gemini API key from https://aistudio.google.com/apikey. ADK automatically
loads the repo root `.env`.

## Run

```bash
# Standalone chat loop:
uv run apps/adk_agent/chat.py

# Or via the ADK CLI (from the repo root):
uv run adk run apps/adk_agent   # interactive terminal chat
uv run adk web                  # browser UI; pick "adk_agent"
```

## Example

```
you: what's in the current directory and what python version do I have?
  → tool: run_shell_command({'command': 'ls && python3 --version'})
  ← tool returned
agent: You're in the AgentGuard repo root ... and you're on Python 3.11.
```

## Configuration (env vars)

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_API_KEY` | — | Gemini API key (required). |
| `ADK_MODEL` | `gemini-2.0-flash` | Model the agent uses. |
| `ADK_COMMAND_TIMEOUT_SECONDS` | `60` | Max seconds per command. |
| `ADK_MAX_OUTPUT_CHARS` | `20000` | Output truncation cap per command. |
| `ADK_GMAIL_MCP_ENABLED` | `false` | Enables the Docker-backed Gmail MCP toolset. |
| `GMAIL_MCP_DOCKER_IMAGE` | `agentguard-gmail-mcp:artymclabin` | Local Docker image for the ArtyMcLabin Gmail MCP server. |
| `GMAIL_MCP_CREDENTIALS_VOLUME` | `mcp-gmail` | Docker volume storing Gmail OAuth credentials. |
| `GMAIL_MCP_TOOL_PREFIX` | `gmail` | Prefix for exposed ADK tool names. |

## Gmail MCP via Docker

This app is wired for the ArtyMcLabin Gmail MCP server, built locally so you do
not accidentally use a different public Gmail image.

```bash
mkdir -p external
git clone https://github.com/ArtyMcLabin/Gmail-MCP-Server.git external/Gmail-MCP-Server
cd external/Gmail-MCP-Server
git checkout a730a11187d00d4c0616940d97c4553770566d0e
docker build -t agentguard-gmail-mcp:artymclabin .
```

Create a Google Cloud OAuth client, enable the Gmail API, download the OAuth key
JSON, then authenticate the Docker volume once:

```bash
docker run -i --rm \
  --mount type=bind,source=/absolute/path/gcp-oauth.keys.json,target=/gcp-oauth.keys.json,readonly \
  -v mcp-gmail:/gmail-server \
  -e GMAIL_OAUTH_PATH=/gcp-oauth.keys.json \
  -e GMAIL_CREDENTIALS_PATH=/gmail-server/credentials.json \
  -p 3000:3000 \
  agentguard-gmail-mcp:artymclabin \
  auth --scopes=gmail.readonly,gmail.compose
```

Then set `ADK_GMAIL_MCP_ENABLED=true` in the repo root `.env` and run the
chat loop. The agent exposes only `search_emails`, `read_email`, `draft_email`,
`send_email`, and `send_draft`, prefixed as Gmail tools. AgentGuard records all
proposed Gmail sends and blocks send tools unless the current user turn
explicitly asks to send.

The runtime Docker command expects both OAuth files in the `mcp-gmail` volume:
`/gmail-server/gcp-oauth.keys.json` and `/gmail-server/credentials.json`.

## ⚠️ Safety

`run_shell_command` runs **arbitrary shell commands with your user's
permissions**. Only use it in an environment you trust, and review what the
agent intends to run before approving destructive actions.

Gmail send tools can deliver real email. Use a test account first, and keep the
OAuth key and Docker credentials volume out of git.
