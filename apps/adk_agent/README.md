# ADK Terminal Assistant

A minimal conversational [Google ADK](https://google.github.io/adk-docs/) agent
you can chat with. It has one tool, `run_shell_command`, that executes commands
on the local machine and returns their output.

## Files

- `agent.py` — defines the `run_shell_command` tool and the `root_agent`.
- `chat.py` — a standalone interactive chat loop (no extra CLI needed).
- `__init__.py` — makes the package discoverable by `adk run` / `adk web`.

## Setup

```bash
uv sync                         # installs deps, incl. google-adk (or: pip install -e .)
cp apps/adk_agent/.env.example apps/adk_agent/.env
# edit apps/adk_agent/.env and set GOOGLE_API_KEY=...
```

Get a Gemini API key from https://aistudio.google.com/apikey. ADK automatically
loads `apps/adk_agent/.env`.

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

## ⚠️ Safety

`run_shell_command` runs **arbitrary shell commands with your user's
permissions**. Only use it in an environment you trust, and review what the
agent intends to run before approving destructive actions.
