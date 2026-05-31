# OpenClaw Productivity Environment UI

Local UI for inspecting and interacting with the virtual productivity environment used
by the `agentguard_productivity` OpenClaw trace agent.

It shows:

- email inbox, drafts, and sent messages,
- seeded and written files,
- calendar events and created events,
- generated side-effect state,
- stateful chat against the real OpenClaw productivity agent.

Run from the repository root:

```bash
AGENTGUARD_ENV_FILE=.env.openclaw python3 scripts/run_openclaw_productivity_ui.py
```

Then open:

```text
http://127.0.0.1:8765
```

The UI uses the same workspace as the OpenClaw trace agent:

```text
.openclaw-traces/productivity_workspace/
```
