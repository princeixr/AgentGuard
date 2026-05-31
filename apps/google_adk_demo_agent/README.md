# Google ADK Demo Agent

This app is the hackathon-facing governed runtime path.

Current state:

- `run_demo.py` builds a deterministic `AgentGuardTraceV1`.
- The trace is evaluated by `AgentGuardFirewallV1`.
- The resulting feature, score, decision, live-event, and session-risk artifacts are
  written under `data/traces/v1/google_adk_demo/`.

Planned live path:

```text
Google ADK agent proposes MCP tool call
    -> GoogleADKAdapter builds AgentGuardTraceV1
    -> AgentGuardFirewallV1 evaluates before execution
    -> adapter enforces GuardDecisionV1
    -> tool executes only when permitted
```

Run the current smoke path:

```bash
PYTHONPATH=src python3 apps/google_adk_demo_agent/run_demo.py
```

