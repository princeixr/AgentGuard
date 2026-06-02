# AgentGuard Elastic Storage

Status: verified against Elastic Cloud Serverless.

Last updated: 2026-06-01

## Purpose

Elastic stores canonical AgentGuard v1 records so historical traces and live traces can
be searched during runtime governance.

`data/elastic/` is the database workspace for this project. It is not the database
itself; the Elastic cluster is the database. The workspace stores checked-in mapping
snapshots, reusable query bodies, notebooks for inspection, and ignored local exports.

The first implemented path is:

```text
data/traces/v1/openclaw/traces.jsonl
    -> scripts/ingest_openclaw_traces_to_elastic.py
    -> agentguard-traces-v1
```

The first verified end-to-end checkpoint is recorded in
`data/elastic/checkpoints/2026-06-01_elastic_cloud_checkpoint.md`.

## Implemented Code

```text
src/agentguard/storage/
├── elastic_config.py     environment-based Elastic config and index names
├── elastic_client.py     dependency-free HTTP client using urllib
├── index_templates.py    Elasticsearch mappings for v1 record stores
└── elastic_store.py      setup, ingest, and trace search helpers
```

Database workspace:

```text
data/elastic/
├── README.md
├── mappings/    mapping snapshots generated from index_templates.py
├── queries/     reusable Elasticsearch query bodies
├── notebooks/   lightweight database inspection notebooks
├── checkpoints/ verified database setup and ingest milestones
└── exports/     ignored local exports from Elastic
```

Governance integration:

```text
src/agentguard/governance/
├── retrieval_v1.py       retrieval provider protocol and no-op provider
├── elastic_retrieval.py  Elastic search results -> RetrievalFeatureV1
├── feature_builder_v1.py consumes retrieval providers
└── firewall_v1.py        optionally mirrors all guard artifacts to Elastic
```

Scripts:

```text
scripts/setup_elastic_indices.py
scripts/ingest_openclaw_traces_to_elastic.py
scripts/query_elastic_traces.py
scripts/replay_traces.py
```

## Environment

```env
AGENTGUARD_ELASTIC_ENABLED=true
ELASTICSEARCH_URL=https://your-elastic-url
ELASTICSEARCH_API_KEY=your-api-key
```

Basic auth is also supported:

```env
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=...
```

## Index Setup

Generate the workspace mapping snapshots:

```bash
python3 scripts/export_elastic_workspace.py
```

Create or update the real Elastic indices:

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/setup_elastic_indices.py
```

This creates or updates:

```text
agentguard-traces-v1
agentguard-live-events-v1
agentguard-trace-features-v1
agentguard-guard-scores-v1
agentguard-guard-decisions-v1
agentguard-session-risk-v1
agentguard-labels-v1
agentguard-scenarios-v1
```

Verified on 2026-06-01 against Elastic cluster
`ecd5d17d80a44eb5b81456b138062893`.

## Ingest OpenClaw Traces

Validate without Elastic:

```bash
python3 scripts/ingest_openclaw_traces_to_elastic.py --dry-run
```

Ingest into Elastic:

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/ingest_openclaw_traces_to_elastic.py
```

The document ID is `trace_id`, and the document body is the full `AgentGuardTraceV1`.

## Replay Through AgentGuard

Replay canonical traces locally:

```bash
python3 scripts/replay_traces.py --limit 5 --namespace replay
```

Replay and mirror traces, features, scores, decisions, live events, and session risk to
Elastic:

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/replay_traces.py \
  --elastic \
  --trace-file data/traces/v1/openclaw/traces.jsonl \
  --namespace openclaw_replay
```

This is the current path for creating Elastic decision memory from historical OpenClaw
traces.

Verified replay output on 2026-06-01:

```text
agentguard-traces-v1           7 documents
agentguard-live-events-v1      21 documents
agentguard-trace-features-v1   7 documents
agentguard-guard-scores-v1     7 documents
agentguard-guard-decisions-v1  7 documents
agentguard-session-risk-v1     4 documents
agentguard-labels-v1           0 documents
agentguard-scenarios-v1        0 documents
```

## Query Similar Traces

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/query_elastic_traces.py --size 5
```

The current query uses exact filters for domain/tool category plus lexical multi-match
over retrieval text, intent, trajectory, and argument summary.

## Runtime Firewall Integration

`AgentGuardFirewallV1` can now be constructed with Elastic enabled:

```python
firewall = AgentGuardFirewallV1(enable_elastic=True)
```

When enabled, the firewall:

1. writes the proposed `AgentGuardTraceV1` locally and to Elastic,
2. retrieves similar historical traces from Elastic through `ElasticTraceRetrievalProvider`,
3. stores the derived `TraceFeatureV1`,
4. scores and decides,
5. stores `GuardScoreV1`, `GuardDecisionV1`, `LiveEventV1`, and `SessionRiskStateV1`.

The retrieval provider uses labels or previous guard decisions to classify retrieved
neighbors into approved and blocked evidence. If no labels/decisions exist yet, it still
records `top_k`, but approved/blocked similarity remains zero.

Next steps:

- populate `agentguard-scenarios-v1`,
- populate `agentguard-labels-v1`,
- combine the current lexical query with semantic/vector retrieval,
- add Kibana data views and dashboards for demo inspection.

## Workspace Rule

`src/agentguard/storage/index_templates.py` is the source of truth for mappings used by
code. `data/elastic/mappings/` is the checked-in database-facing snapshot. Run
`python3 scripts/export_elastic_workspace.py` after changing index templates.
