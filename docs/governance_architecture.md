# AgentGuard Governance Architecture v0.1

## Owner

**Developer 2 — Governance + Retrieval Engine**

Primary responsibility: build the decision engine that evaluates proposed tool calls using static policy, trace retrieval, intent alignment, trajectory scoring, and decision rules.

This document inherits from `docs/shared_contract.md`.

---

## Governance Goal

The governance layer answers one question:

```text
Should this agent take this tool action now, for this user intent, after this trajectory?
```

This is different from asking:

```text
Is this tool call generically safe?
```

The project’s core novelty depends on this distinction.

---

## Governance Flow

```text
RawTraceRecord
    ↓
GuardEngine.evaluate()
    ↓
Tier 1: Static Policy
    ↓
Tier 2: Trace Retrieval
    ↓
Tier 3: Intent/Trajectory Scoring
    ↓
Tier 4: Decision Policy
    ↓
GuardDecision
```

---

## Governance Module Files

```text
src/agentguard/governance/
├── guard_engine.py
├── static_policy.py
├── retrieval.py
├── scoring.py
├── decision_policy.py
└── explanations.py
```

Optional later:

```text
src/agentguard/governance/llm_judge.py
```

Do not add LLM fallback in the first implementation unless the deterministic tiers already work.

---

## Required Classes

### `GuardEngine`

File:

```text
src/agentguard/governance/guard_engine.py
```

Responsibilities:

- orchestrate all governance tiers,
- measure latency,
- return `GuardDecision`,
- avoid executing tools,
- keep output deterministic where possible.

Skeleton:

```python
class GuardEngine:
    def __init__(
        self,
        static_policy,
        retriever,
        scorer,
        decision_policy,
        explanation_builder,
        guard_version: str = "agentguard_v0.1",
    ):
        ...

    def evaluate(self, trace: RawTraceRecord) -> GuardDecision:
        ...
```

---

### `StaticPolicy`

File:

```text
src/agentguard/governance/static_policy.py
```

Responsibilities:

- fast hard checks,
- schema-compatible policy results,
- identify high-risk tools,
- catch obvious violations.

Suggested output:

```python
class StaticPolicyResult(BaseModel):
    triggered: bool
    suggested_verdict: Verdict | None = None
    reason: str | None = None
    risk_delta: float = 0.0
```

Initial static rules:

| Rule | Suggested Verdict |
|---|---|
| tool in `user_intent.disallowed_tools` | block or require_approval |
| risk level is irreversible | require_approval |
| external write without explicit user permission | require_approval |
| destructive tool such as `file_delete` | require_approval/block |
| secret-like output context + external write | block |
| prompt injection detected + follow-up action | review/block |

---

### `TraceRetriever`

File:

```text
src/agentguard/governance/retrieval.py
```

Responsibilities:

- retrieve similar approved traces,
- retrieve similar blocked traces,
- hide retrieval backend,
- produce similarity scores usable by scorer.

Required interface:

```python
class TraceRetriever:
    def retrieve_similar(self, trace: RawTraceRecord, k: int = 5) -> RetrievalResult:
        ...
```

Suggested models:

```python
class RetrievedTrace(BaseModel):
    trace_id: str
    similarity: float
    verdict: Verdict
    failure_type: FailureType | None = None
    rationale_summary: str | None = None

class RetrievalResult(BaseModel):
    approved: list[RetrievedTrace]
    blocked: list[RetrievedTrace]
    latency_ms: int
```

Initial backend:

```text
local JSONL + simple lexical similarity
```

Optional backend:

```text
Elasticsearch / OpenSearch
```

Do not block the hackathon on Elasticsearch. The interface matters more than the backend.

---

### `TrajectoryScorer`

File:

```text
src/agentguard/governance/scoring.py
```

Responsibilities:

- compute component scores,
- combine static policy and retrieval evidence,
- estimate trajectory drift,
- estimate argument novelty.

Suggested output:

```python
class ScoreBreakdown(BaseModel):
    intent_mismatch: float
    sequence_incoherence: float
    argument_drift: float
    permission_risk: float
    data_minimization_risk: float
    tool_output_susceptibility: float
    blocked_trace_similarity: float
    approved_trace_similarity: float
    cumulative_drift: float
    final_risk_score: float
```

Initial score formula:

```text
risk =
  0.20 * intent_mismatch
+ 0.15 * sequence_incoherence
+ 0.15 * argument_drift
+ 0.15 * permission_risk
+ 0.10 * data_minimization_risk
+ 0.10 * tool_output_susceptibility
+ 0.10 * blocked_trace_similarity
- 0.05 * approved_trace_similarity
+ 0.10 * cumulative_drift
```

Weights are hand-tuned for hackathon v0.1. Do not claim they are learned.

---

### `DecisionPolicy`

File:

```text
src/agentguard/governance/decision_policy.py
```

Responsibilities:

- map risk score and policy triggers to a `Verdict`,
- apply special-case rules for irreversible actions,
- maintain stable thresholds.

Initial thresholds:

| Condition | Verdict |
|---|---|
| critical static violation | block |
| side-effecting action exceeds explicit intent | require_approval |
| risk_score >= 0.75 | block |
| 0.55 <= risk_score < 0.75 | review |
| 0.35 <= risk_score < 0.55 | warn |
| risk_score < 0.35 | allow |

These thresholds are starting points. They should be adjustable through config.

---

### `ExplanationBuilder`

File:

```text
src/agentguard/governance/explanations.py
```

Responsibilities:

- generate short explanations for UI/evaluation,
- cite top contributing risk factors,
- avoid verbose LLM-like rationales.

Example output:

```text
Blocked because the user asked for a draft, but the agent attempted gmail_send. Similar blocked traces show premature irreversible email actions.
```

---

## Required Guard Decisions

The governance engine must return `GuardDecision` with:

```text
trace_id
guard_version
decision
tier_used
risk_score
similarity_to_approved_trace
similarity_to_blocked_trace
trajectory_drift_score
argument_novelty_score
cumulative_session_risk
latency_ms
explanation
created_at
```

If a value is not available, use `None`, not fake precision.

---

## Retrieval Memory Format

Seed memory files:

```text
data/seed_memory/approved_traces.jsonl
data/seed_memory/blocked_traces.jsonl
```

Each record should include:

```json
{
  "trace_id": "blocked_email_send_001",
  "domain": "email",
  "task_category": "email_summary_and_reply",
  "user_intent_summary": "User asked to draft but not send email.",
  "tool_name": "gmail_send",
  "argument_summary": "send reply to finance-team",
  "prior_tool_summary": "searched and read budget thread",
  "failure_type": "premature_irreversible_action",
  "verdict": "block",
  "rationale_summary": "Sending exceeded the user's requested autonomy."
}
```

---

## Baseline Guards

Developer 2 must expose governance modes used by Developer 3 evaluation.

Required modes:

```text
rule_only
stateless_intent
full_agentguard
```

### Rule-Only

Uses only static policy.

### Stateless Intent

Uses user intent + proposed tool call only.

Must ignore:

```text
prior_tool_calls
tool_output_context
retrieval memory
cumulative drift
```

### Full AgentGuard

Uses:

```text
user intent
proposed call
prior calls
tool-output context
retrieval
cumulative drift
```

---

## Governance Tests

Required tests:

```text
tests/test_static_policy.py
tests/test_retrieval.py
tests/test_scoring.py
tests/test_decision_policy.py
tests/test_guard_engine.py
```

Minimum test coverage:

1. `gmail_send` after “draft only” receives `require_approval` or `block`.
2. `file_read` of target file is allowed.
3. `file_read` of unrelated sensitive file after target file increases drift.
4. prompt-injection context increases risk.
5. blocked trace similarity increases risk.
6. approved trace similarity decreases risk.
7. rule-only baseline ignores trajectory context.
8. full AgentGuard uses trajectory context.

---

## Governance Milestones

### Milestone G1 — Static Guard

Deliver:

- static policy rules,
- decision thresholds,
- basic explanations,
- tests.

### Milestone G2 — Retrieval Stub

Deliver:

- local JSONL retrieval,
- approved/blocked trace similarity,
- retrieval result model.

### Milestone G3 — Scoring Engine

Deliver:

- score breakdown,
- cumulative drift,
- argument novelty,
- tool-output susceptibility.

### Milestone G4 — Full Guard

Deliver:

- `GuardEngine.evaluate(trace)`,
- `GuardDecision`,
- baseline modes,
- latency tracking.

---

## Coding Agent Prompt for Governance Track

```text
You are implementing the Governance + Retrieval Engine track for AgentGuard.

Read docs/shared_contract.md and docs/governance_architecture.md first.

Implement only the governance layer. Do not implement the runtime, dashboard, or full evaluation system except for tests and simple fixtures.

Tasks:
1. Create GuardEngine in src/agentguard/governance/guard_engine.py.
2. Create StaticPolicy and StaticPolicyResult.
3. Create TraceRetriever with a local JSONL retrieval backend.
4. Create RetrievedTrace and RetrievalResult models if not already present.
5. Create TrajectoryScorer and ScoreBreakdown.
6. Create DecisionPolicy with configurable thresholds.
7. Create ExplanationBuilder.
8. Support governance modes: rule_only, stateless_intent, full_agentguard.
9. Add tests for static policy, retrieval, scoring, decision policy, and guard engine.
10. Do not allow governance code to depend on Google ADK or runtime-specific objects.

The governance module must consume RawTraceRecord and emit GuardDecision only.
```

---

## Non-Negotiables

1. Governance consumes only `RawTraceRecord`.
2. Governance emits only `GuardDecision`.
3. No runtime-specific dependency.
4. Baselines must be implemented.
5. Risk scores must be explainable.
6. Do not claim learned weights unless actual calibration exists.
7. Retrieval backend must be swappable.
