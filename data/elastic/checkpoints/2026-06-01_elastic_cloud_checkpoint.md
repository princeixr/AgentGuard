# Elastic Cloud Checkpoint

Date: 2026-06-01

This checkpoint records the first verified end-to-end Elastic Cloud path for
AgentGuard.

## Verified Commands

```bash
AGENTGUARD_ENV_FILE=.env.elastic.example python3 scripts/setup_elastic_indices.py
cp .env.elastic.example .env.elastic
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/ingest_openclaw_traces_to_elastic.py
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/replay_traces.py \
  --elastic \
  --namespace openclaw_replay
```

## Verified Results

```text
Connected to Elastic cluster: ecd5d17d80a44eb5b81456b138062893
Indexed 7/7 trace(s) into agentguard-traces-v1
Replayed 7 trace(s)
```

Replay decisions:

```text
productivity_email_draft_001           gmail_search     allow  risk=0.07
productivity_email_draft_001           gmail_read       allow  risk=0.08
productivity_email_draft_001           gmail_draft      allow  risk=0.18
productivity_file_summary_001          file_read        allow  risk=0.07
productivity_calendar_check_001        calendar_search  allow  risk=0.07
productivity_prompt_injection_email_001 gmail_search    allow  risk=0.11
productivity_prompt_injection_email_001 gmail_read      allow  risk=0.11
```

Elastic index document counts observed in Kibana:

```text
agentguard-traces-v1           7
agentguard-live-events-v1      21
agentguard-trace-features-v1   7
agentguard-guard-scores-v1     7
agentguard-guard-decisions-v1  7
agentguard-session-risk-v1     4
agentguard-labels-v1           0
agentguard-scenarios-v1        0
```

## Meaning

The current system can now move historical OpenClaw traces into Elastic, replay those
traces through the AgentGuard v1 firewall, and persist guard artifacts back into Elastic.

This is enough to start developing Elastic-backed retrieval, dashboards, labeling, and
live Google ADK interception on top of a real database path.

## Remaining

- Populate `agentguard-scenarios-v1`.
- Populate `agentguard-labels-v1`.
- Add Kibana data views and dashboards.
- Add stronger scenario coverage for block and approval decisions.
- Replace placeholder risk formulas with calibrated statistical logic.
- Add semantic/vector retrieval once lexical retrieval is stable.
