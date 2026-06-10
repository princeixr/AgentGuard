# Configuration

## AgentGuard Product

Core variables:

- `AGENTGUARD_API_KEY`: bearer token required by SDK clients.
- `AGENTGUARD_WEB_ORIGINS`: comma-separated dashboard origins.
- `AGENTGUARD_TRACE_ROOT`: trace/event storage root.
- `AGENTGUARD_APPROVAL_ROOT`: approval storage root.
- `GOOGLE_API_KEY`: required for Gemini-backed intent/Tier 3.

## Google ADK Agent

- `AGENTGUARD_BASE_URL`: AgentGuard API URL.
- `AGENTGUARD_API_KEY`: same key configured on AgentGuard.
- `AGENTGUARD_APPROVAL_WAIT_TIMEOUT_SECONDS`: max wait for human approval.
