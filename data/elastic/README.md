# AgentGuard Elastic Workspace

This folder is the database workspace for AgentGuard.

Elastic itself is the database. This folder stores the files developers use to create,
inspect, test, and reason about that database:

```text
data/elastic/
├── mappings/    checked-in snapshots of Elastic index mappings
├── queries/     reusable Elasticsearch query bodies
├── notebooks/   exploratory database inspection notebooks
├── checkpoints/ verified database setup and ingest milestones
└── exports/     ignored local exports from Elastic
```

Production code remains in:

```text
src/agentguard/storage/
```

Operational scripts remain in:

```text
scripts/
```

## Generate Mapping Snapshots

The mapping snapshots are generated from `src/agentguard/storage/index_templates.py`.

```bash
python3 scripts/export_elastic_workspace.py
```

## Create Indices

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/setup_elastic_indices.py
```

## Ingest Historical OpenClaw Traces

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/ingest_openclaw_traces_to_elastic.py
```

## Create Decision Memory

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/replay_traces.py \
  --elastic \
  --namespace openclaw_replay
```

## Current Checkpoint

The first verified Elastic Cloud checkpoint is:

```text
data/elastic/checkpoints/2026-06-01_elastic_cloud_checkpoint.md
```

It confirms:

```text
7 OpenClaw traces indexed
7 guard decisions indexed
7 guard scores indexed
7 trace features indexed
21 live events indexed
4 session-risk states indexed
```

## Query

Start with the JSON bodies in `queries/` or the notebooks in `notebooks/`.

The most important index is:

```text
agentguard-traces-v1
```

That index stores one `AgentGuardTraceV1` document per proposed tool call.
