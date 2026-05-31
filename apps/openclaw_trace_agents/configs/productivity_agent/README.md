# OpenClaw Productivity Trace Agent

This configuration is the first real OpenClaw trace-generation target for AgentGuard.

It uses one OpenClaw agent with access to email-like, file-like, and calendar-like local
tools. The tools are deterministic and operate on seeded mock data so traces are
repeatable, but the planning loop is still the real OpenClaw agent and model runtime.

## Agent Id

```text
agentguard_productivity
```

## Workspace

The setup script copies `workspace_template/` into:

```text
.openclaw-traces/productivity_workspace/
```

That workspace contains:

```text
AGENTS.md                    behavior contract for OpenClaw
TOOLS.md                     concrete tool command reference
data/productivity_seed.json  seeded inbox, files, and calendar data
tools/productivity_tool.py   deterministic local tool CLI
state/                       generated drafts and simulated side effects
```

## Setup

From the repository root:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/setup_openclaw_productivity_agent.py
```

Then run collection with:

```bash
set -a
source .env.openclaw
set +a

AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/collect_openclaw_traces.py \
  --real-openclaw \
  --profile "$OPENCLAW_TRACE_PROFILE" \
  --agent "$OPENCLAW_TRACE_PRODUCTIVITY_AGENT" \
  --scenario-file data/scenarios/productivity_agent_scenarios.jsonl \
  --runs-per-scenario 1 \
  --openclaw-raw-root "$OPENCLAW_RAW_ARTIFACT_ROOT" \
  --trace-root "$AGENTGUARD_RAW_TRACE_ROOT" \
  --timeout-seconds 180
```

## Trace Semantics

OpenClaw calls the local tool through its native `exec` tool. The transcript reader maps
commands that invoke `tools/productivity_tool.py` to semantic AgentGuard tool names:

```text
gmail_search
gmail_read
gmail_draft
gmail_send
file_search
file_read
file_write
file_delete
calendar_search
calendar_read
calendar_create_event
```

The source OpenClaw tool call id and transcript record index are still preserved in
benchmark provenance.
