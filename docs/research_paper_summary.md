# Research Paper Summary

The drafted paper frames AgentGuard as trace-conditioned runtime governance:
the guard evaluates whether this agent should take this action now, for this
user goal, after this trajectory.

For implementation, the paper implies two distinct responsibilities:

1. The Google ADK demo proves the hackathon-facing runtime governance story.
2. OpenClaw and other live agents generate raw traces for research benchmarking.

Raw traces, labels, and guard outputs must remain separate.

