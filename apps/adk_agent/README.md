# ADK Terminal Assistant

A minimal conversational [Google ADK](https://google.github.io/adk-docs/) agent
you can chat with. It has one local tool, `run_shell_command`, and can expose
any MCP servers declared in `config/adk_mcp_servers.toml`.

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
| `AGENTGUARD_ADK_TRACE_NAMESPACE` | `google_adk` | Namespace for local v1 trace artifacts. |
| `AGENTGUARD_TRACE_ROOT` | `data/traces` | Root directory for local trace artifacts. |
| `AGENTGUARD_ADK_ELASTIC_ENABLED` | unset | Optional ADK-only override for `AGENTGUARD_ELASTIC_ENABLED`. |
| `AGENTGUARD_ADK_FAIL_ON_ELASTIC_ERROR` | `false` | When false, live ADK continues if Elastic indexing/retrieval fails after startup. |
| `ADK_MCP_CONFIG_PATH` | `config/adk_mcp_servers.toml` | Optional path override for the declarative MCP registry. |

## Plugging In MCP Servers

MCP servers are configured in `config/adk_mcp_servers.toml`. Adding another
integration normally requires only:

1. Add a `[[servers]]` block.
2. Put required secrets in the repo root `.env`.
3. Restart the agent and check its startup status.

No Python changes or per-tool configuration are normally required. When ADK
connects, AgentGuard reads the MCP server's tool names, descriptions, schemas,
and annotations, then automatically classifies the discovered tools. The
registry supports stdio commands, including Docker and package runners, plus
remote Streamable HTTP servers.

### Minimal Server Configuration

Every server requires:

| Field | Purpose |
| --- | --- |
| `id` | Unique server identity recorded in traces as `mcp_server`. |
| `prefix` | Unique tool-name prefix. A raw tool named `read_item` becomes `example_read_item`. |
| `enabled` | Whether the runtime should connect to the server. |
| `transport` | Either `stdio` or `streamable_http`. |

```toml
[[servers]]
id = "example"
prefix = "example"
enabled = true
transport = "streamable_http"

[servers.streamable_http]
url = "https://example.test/mcp"
headers = { Authorization = "Bearer ${EXAMPLE_MCP_TOKEN}" }
```

All tools advertised by the server are exposed to ADK and registered with
AgentGuard. Clear read operations are automatically read-only; clear write and
destructive operations are classified conservatively; ambiguous tools inherit
the fixed safe fallback of `high_risk` with confirmation required.

### Automatic Tool Discovery

Discovery uses MCP annotations first, then the tool name and description:

| Discovered behavior | Automatic policy |
| --- | --- |
| MCP `readOnlyHint = true`, or clear `get`, `list`, `read`, or `search` tool | `read_only`, no confirmation |
| Clear `draft`, `preview`, or `stage` tool | `low_side_effect`, no confirmation |
| Clear `create`, `update`, `write`, `send`, `publish`, or similar tool | `external_write`, confirmation required |
| MCP `destructiveHint = true`, or clear `delete`, `remove`, `merge`, or similar tool | `irreversible`, confirmation required |
| Unclear tool | `high_risk`, confirmation required |

New tools added by an MCP server are discovered automatically the next time the
agent starts or refreshes that toolset.

### Stdio MCP Server

Use `stdio` for a locally installed executable, package runner, or Docker
container:

```toml
[[servers]]
id = "filesystem"
prefix = "files"
enabled = true
transport = "stdio"

[servers.stdio]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/absolute/allowed/path"]
env = { FILESYSTEM_MODE = "readonly" }

```

The command must be available on `PATH`. For Docker-backed servers, put the
complete non-interactive `docker run -i --rm ...` invocation in
`servers.stdio.args`. Do not use `-t`; MCP communicates over stdin/stdout.

### Streamable HTTP MCP Server

Use `streamable_http` for a remote MCP endpoint:

```toml
[[servers]]
id = "remote_project"
prefix = "project"
enabled = true
transport = "streamable_http"

[servers.streamable_http]
url = "https://mcp.example.com/mcp"
headers = { Authorization = "Bearer ${PROJECT_MCP_TOKEN}" }
```

HTTP server readiness currently verifies that the configuration is valid; the
actual network connection is established by ADK when the toolset is used.

### Open-source Google Workspace MCP Server

The checked-in registry runs Google's open-source
[`gemini-cli-extensions/workspace`](https://github.com/gemini-cli-extensions/workspace)
server through `npx`. It works with normal Google accounts and does not depend
on the Developer Preview-only `*mcp.googleapis.com` endpoints.

One MCP process exposes Gmail, Calendar, Drive, and Chat. Tools are
self-discovered under names such as:

```text
workspace_calendar_listEvents
workspace_drive_search
workspace_gmail_search
workspace_chat_listSpaces
```

The existing Docker Gmail server remains available under `gmail_local_*`.

The first Workspace tool call opens Google's authorization page in your
browser. Complete sign-in there; the server stores and refreshes credentials
through macOS Keychain under `gemini-cli-workspace-oauth`. Later agent runs
reuse that credential without ADK-specific OAuth configuration.

The package is pinned to `v0.0.8` in `config/adk_mcp_servers.toml`. Its first
startup can take longer while `npx` downloads and builds the package.

The checked-in `WORKSPACE_FEATURE_OVERRIDES` disables Docs, People, Slides,
Sheets, Time, and Tasks so only the requested Gmail, Calendar, Drive, and Chat
services are exposed. Their read and write feature groups remain enabled, so
Google may request broad write scopes. AgentGuard still requires approval for
discovered write and destructive tools; the terminal demo blocks those actions
because it does not yet have an approval UI.

To sign in with another account, stop the agent, open **Keychain Access**, find
the `gemini-cli-workspace-oauth` item, delete it, and invoke a Workspace tool
again.

### Secrets and Environment Variables

Use `${VARIABLE_NAME}` anywhere inside stdio commands, arguments, environment
values, HTTP URLs, or headers:

```toml
[servers.stdio]
command = "docker"
args = ["run", "-i", "--rm", "-e", "API_TOKEN=${PROJECT_MCP_TOKEN}", "project-mcp:latest"]

[servers.streamable_http]
url = "${PROJECT_MCP_URL}"
headers = { Authorization = "Bearer ${PROJECT_MCP_TOKEN}" }
```

Define referenced values in the repo root `.env`:

```dotenv
PROJECT_MCP_URL=https://mcp.example.com/mcp
PROJECT_MCP_TOKEN=replace-with-real-token
```

Missing referenced environment variables cause startup to fail with the
variable name, but not its value. Resolved values are redacted from recorded MCP
errors. Never put real credentials directly in the TOML file.

### Configuration Rules

- Server IDs and prefixes must be unique.
- `prefix` may contain underscores; longer matching prefixes are resolved first.
- An enabled stdio server is omitted when its command is unavailable on `PATH`.
- All server tools are exposed because `tool_filter` is intentionally unset.
- Tools self-discover metadata from MCP annotations, names, and descriptions.
- Tools that cannot be classified become `high_risk` with confirmation required.
- TOML contains connection configuration only; it cannot override tool metadata.
- The registry is loaded when the Python process imports the agent. Restart after
  editing TOML or `.env`.
- Use `ADK_MCP_CONFIG_PATH` to load a different TOML file. Relative paths are
  resolved from the repository root.

### Add an MCP Server Checklist

1. Read the MCP server documentation and identify its transport and startup command.
2. Test the server command independently and ensure it runs non-interactively.
3. Add a disabled server block with a unique ID and prefix.
4. Add secrets to `.env` through `${VARIABLE_NAME}` references.
5. Enable the server, restart the agent, and confirm startup reports it as `ready`.
6. Test discovered read-only tools first.
7. Confirm discovered write tools produce `require_approval`.

### Validate and Troubleshoot

Run the registry tests after editing configuration:

```bash
uv run pytest -q tests/test_mcp_registry.py tests/test_google_adk_runtime.py
```

Start the standalone chat to see each configured server's status:

```bash
uv run apps/adk_agent/chat.py
```

Common failures:

| Message or behavior | Meaning |
| --- | --- |
| `disabled` | Set `enabled = true` when the server is ready to use. |
| `command '...' is not available on PATH` | Install the command or use an absolute command path. |
| `references missing environment variable(s)` | Add the named variable to `.env` and restart. |
| Duplicate ID or prefix error | Give every server a distinct `id` and `prefix`. |
| Unknown tool requires approval | Its behavior was ambiguous, so AgentGuard conservatively requires approval. |
| Server marked ready but HTTP call fails | Check endpoint reachability, authentication headers, and remote server logs. |

### Local Gmail Example

The checked-in registry includes an enabled local Gmail Docker configuration. Gmail
read, draft, update, delete, reply, and other tools are discovered
automatically. Build and authenticate its Docker image, ensure the `mcp-gmail`
Docker volume contains the OAuth files, and start Docker before running the
agent. Its tools use the `gmail_local_*` prefix.

Gmail send and reply tools are naturally inferred as external writes and require
approval. Because this terminal demo has no approval UI, those actions are
stopped before execution when approval enforcement is enabled.

## Elastic-backed Runtime Memory

Set `AGENTGUARD_ELASTIC_ENABLED=true` plus `ELASTICSEARCH_URL` and auth to mirror live
ADK traces, features, scores, decisions, live events, and session risk into Elastic.
When Elastic is enabled, the firewall also retrieves similar historical traces and maps
their labels/decisions into retrieval features before scoring the current tool call.

Use `AGENTGUARD_ADK_ELASTIC_ENABLED=false` to keep the ADK agent local-only even when
global Elastic is enabled for other scripts.

The Gmail example's Docker command expects both OAuth files in the `mcp-gmail`
volume: `/gmail-server/gcp-oauth.keys.json` and
`/gmail-server/credentials.json`.

## ⚠️ Safety

`run_shell_command` runs **arbitrary shell commands with your user's
permissions**. Only use it in an environment you trust, and review what the
agent intends to run before approving destructive actions.

Gmail send tools can deliver real email. Use a test account first, and keep the
OAuth key and Docker credentials volume out of git.
