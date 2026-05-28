# Demo Script

## Demo 1: Draft vs Send

Show a user asking for an email draft. The agent proposes `gmail_send`.
AgentGuard returns `require_approval` or `block` because sending exceeds intent.

## Demo 2: File Scope Creep

Show the agent reading the requested file, then proposing an unrelated sensitive read.
AgentGuard flags trajectory drift.

## Demo 3: Prompt Injection From Tool Output

Show a tool output containing an instruction-like payload. The agent attempts a follow-up
action induced by that output. AgentGuard flags tool-output susceptibility.

