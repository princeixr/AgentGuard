# ADK Terminal Assistant

A minimal conversational [Google ADK](https://google.github.io/adk-docs/) agent
you can chat with. It has one local tool, `run_shell_command`, and can
optionally expose a Docker-backed Gmail MCP server.

AgentGuard is wired through ADK tool callbacks. Every proposed tool call becomes an
`AgentGuardTraceV1`, is evaluated by `AgentGuardFirewallV1` before execution, and is
then mapped to `allow`, `require_approval`, or unconditional `block`.

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
| `AGENTGUARD_ADK_ENFORCE_APPROVAL` | `true` | When true, `require_approval` returns a synthetic response and the tool is not executed. |
| `AGENTGUARD_FORCE_BLOCK` / `FORCE_BLOCK` | `false` | Demo/test override that records a `block` decision and prevents every ADK tool call from executing. |
| `AGENTGUARD_FIREWALL_MODE` | `v1` | `v1`, `v2_shadow`, or `v2`; controls whether V2 records evidence or owns enforcement. |
| `AGENTGUARD_TIER_1_ENABLED` | `true` | Enables the V2 deterministic tier. |
| `AGENTGUARD_TIER_2_ENABLED` | `false` | Enables the V2 Tier 2 semantic boundary. Current implementation records a conservative placeholder. |
| `AGENTGUARD_TIER_3_ENABLED` | `false` | Enables the Gemini-backed V2 Tier 3 LLM judge when escalation is needed. |
| `AGENTGUARD_TIER3_ENFORCEMENT_ENABLED` | `false` | Allows Tier 3 output to affect the V2 combiner. Keep false for shadow testing. |
| `AGENTGUARD_TIER_CONFIDENCE_THRESHOLD` | `0.75` | Confidence threshold used to escalate between enabled tiers. |
| `AGENTGUARD_TIER3_MODEL` | `gemini-2.5-flash` | Gemini model used by the Tier 3 judge. |
| `AGENTGUARD_MOCK_PIPELINE_ONLY` | `false` | Evaluates and logs the full guard pipeline but never executes the proposed tool. Recommended for cloud/team tests. |
| `AGENTGUARD_ADK_TRACE_NAMESPACE` | `google_adk` | Namespace for local v1 trace artifacts. |
| `AGENTGUARD_TRACE_ROOT` | `data/traces` | Root directory for local trace artifacts. |
| `AGENTGUARD_ADK_ELASTIC_ENABLED` | unset | Optional ADK-only override for `AGENTGUARD_ELASTIC_ENABLED`. |
| `AGENTGUARD_ADK_FAIL_ON_ELASTIC_ERROR` | `false` | When false, live ADK continues if Elastic indexing/retrieval fails after startup. |
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
`send_email`, and `send_draft`, prefixed as Gmail tools. AgentGuard records tool
category, risk, side-effect type, confirmation requirement, and MCP server metadata for
these tools before the firewall decision.

## Elastic-backed Runtime Memory

Set `AGENTGUARD_ELASTIC_ENABLED=true` plus `ELASTICSEARCH_URL` and auth to mirror live
ADK traces, features, scores, decisions, live events, and session risk into Elastic.
When Elastic is enabled, the firewall also retrieves similar historical traces and maps
their labels/decisions into retrieval features before scoring the current tool call.

Use `AGENTGUARD_ADK_ELASTIC_ENABLED=false` to keep the ADK agent local-only even when
global Elastic is enabled for other scripts.

## V2 Tiered Runtime

For Tier 3 shadow evaluation:

```bash
export GOOGLE_API_KEY="..."
export AGENTGUARD_FIREWALL_MODE=v2
export AGENTGUARD_TIER_1_ENABLED=true
export AGENTGUARD_TIER_2_ENABLED=false
export AGENTGUARD_TIER_3_ENABLED=true
export AGENTGUARD_TIER3_ENFORCEMENT_ENABLED=false
```

For safe shared testing, add:

```bash
export AGENTGUARD_MOCK_PIPELINE_ONLY=true
```

Mock-pipeline mode still writes trace, V1, V2, tier, combiner, and runtime events, but
the ADK tool is not executed.

The runtime Docker command expects both OAuth files in the `mcp-gmail` volume:
`/gmail-server/gcp-oauth.keys.json` and `/gmail-server/credentials.json`.

## ⚠️ Safety

`run_shell_command` runs **arbitrary shell commands with your user's
permissions**. Only use it in an environment you trust, and review what the
agent intends to run before approving destructive actions.

Gmail send tools can deliver real email. Use a test account first, and keep the
OAuth key and Docker credentials volume out of git.
