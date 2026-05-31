# AgentGuard Elastic Storage

Status: initial implementation.

Last updated: 2026-05-31

## Purpose

Elastic stores canonical AgentGuard v1 records so historical traces and live traces can
be searched during runtime governance.

The first implemented path is:

```text
data/traces/v1/openclaw/traces.jsonl
    -> scripts/ingest_openclaw_traces_to_elastic.py
    -> agentguard-traces-v1
```

## Implemented Code

```text
src/agentguard/storage/
├── elastic_config.py     environment-based Elastic config and index names
├── elastic_client.py     dependency-free HTTP client using urllib
├── index_templates.py    Elasticsearch mappings for v1 record stores
└── elastic_store.py      setup, ingest, and trace search helpers
```

Scripts:

```text
scripts/setup_elastic_indices.py
scripts/ingest_openclaw_traces_to_elastic.py
scripts/query_elastic_traces.py
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

## Query Similar Traces

```bash
AGENTGUARD_ENV_FILE=.env.elastic python3 scripts/query_elastic_traces.py --size 5
```

The current query uses exact filters for domain/tool category plus lexical multi-match
over retrieval text, intent, trajectory, and argument summary.

Next step: replace or combine this with semantic/vector retrieval and feed the result
into `TraceFeatureV1.retrieval`.
