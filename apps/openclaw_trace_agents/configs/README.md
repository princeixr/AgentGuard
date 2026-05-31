# OpenClaw Agent Configs

This directory contains real OpenClaw agent configuration templates used only for trace
generation.

The active target is one consolidated productivity agent:

- `productivity_agent/`

It exposes email-like, file-like, and calendar-like deterministic local tools in one
workspace. That keeps the first benchmark collection path simple while still covering
cross-domain agent behavior.

Earlier three-agent placeholders are retained as planning notes:

- `email_agent/`
- `file_agent/`
- `calendar_agent/`

Each configuration should define a controlled OpenClaw agent with a restricted tool
surface and sandbox/mock side effects. These agents are dataset generators, not
AgentGuard enforcement targets.
