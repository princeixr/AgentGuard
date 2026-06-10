# AgentGuard Evaluation Architecture

Status: current implemented v1 architecture.

Last updated: 2026-05-30

## Evaluation Goal

Evaluation should prove whether trajectory-aware AgentGuard decisions outperform simple
baseline policies on realistic tool-use traces.

The evaluation input contract is `AgentGuardTraceV1`.

## Dataset Sources

```text
OpenClaw productivity traces
Google ADK demo traces
mock traces
synthetic/adversarial scenarios
```

All sources must be converted to `AgentGuardTraceV1` before evaluation.

## Implemented Files

```text
src/agentguard/evaluation/
├── dataset_models.py    benchmark dataset wrappers and manifest models
├── labels.py            label loading helpers
├── metrics.py           metric helpers
├── replay.py            replays AgentGuardTraceV1 through AgentGuardFirewallV1
├── baseline_guards.py   baseline factory returning the current v1 firewall
├── scenarios.py         scenario loading helpers
└── reports.py           report helpers
```

## Evaluation Flow

```text
AgentGuardTraceV1 dataset
    -> labels loaded separately
    -> replay runner applies guard or baseline
    -> GuardDecisionV1 outputs
    -> metrics compare decisions against labels
    -> report artifacts for demo and paper
```

## Label Contract

Labels use `LabelRecordV1` and must be stored separately from traces and guard outputs.

Important label dimensions:

- intent relevance,
- sequence coherence,
- argument appropriateness,
- permission sensitivity,
- data minimization,
- tool-output susceptibility,
- overall appropriateness,
- gold verdict.

## Current Status

Evaluation scaffolding is in place. The replay path can run `AgentGuardTraceV1` records
through the current v1 firewall. Full benchmark calibration still needs:

- a larger OpenClaw-derived dataset,
- human or LLM-assisted labels,
- calibrated baselines,
- Elastic-backed retrieval features,
- score threshold tuning.
