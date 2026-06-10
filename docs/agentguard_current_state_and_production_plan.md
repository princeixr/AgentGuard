# AgentGuard Current State and Production Logic Plan

Last audited: 2026-06-07

> The broad production roadmap below is not the committed demo scope. The realistic
> implementation target, verification gates, and delivery estimate are defined in
> [agentguard_realistic_demo_scope.md](agentguard_realistic_demo_scope.md).

## Executive Summary

AgentGuard currently has a functional end-to-end governance pipeline around the Google
ADK agent:

```text
Google ADK proposes a tool call
    -> before_tool_callback intercepts it
    -> AgentGuard builds a canonical trace
    -> features are extracted
    -> a deterministic risk score is calculated
    -> policy rules choose allow/warn/review/require_approval/block
    -> the decision and evidence are persisted
    -> allow executes; require_approval or block can stop execution
    -> lifecycle events are exposed to the dashboard
```

This is real interception and real enforcement. It is not currently a production-quality
behavioral security model.

The strongest parts are the runtime boundary, canonical data contracts, persistence,
agent ownership fields, trace replay, dashboard queries, and explicit policy enforcement.
The weakest parts are intent understanding, argument analysis, trajectory statistics,
retrieval quality, risk calibration, policy configuration, durable approval state, and
evaluation coverage.

The current scorer even identifies itself as a "Mathematical placeholder scorer." Its
scores are useful for demonstrating the product flow, but they must not be interpreted as
calibrated probabilities of malicious behavior.

## Current Runtime Flow

### 1. Google ADK interception

`examples/google_adk_agent/agent.py` registers:

- `before_tool_callback`
- `after_tool_callback`
- `on_tool_error_callback`

The before callback runs before the actual shell or Gmail tool. It creates or reuses a
`GoogleADKTraceSession`, records the proposed call, and invokes
`AgentGuardFirewallV1.intercept()`.

Runtime enforcement currently maps decisions as follows:


| Guard decision     | Runtime action                                      |
| ------------------ | --------------------------------------------------- |
| `allow`            | Execute the tool                                    |
| `warn`             | Execute the tool                                    |
| `review`           | Treat as `require_approval`                         |
| `require_approval` | Stop execution when approval enforcement is enabled |
| `block`            | Always stop execution                               |


`AGENTGUARD_FORCE_BLOCK=true` is a demo/testing override. It produces a real persisted
`block` decision with the rule `force_block_enabled` and prevents execution.

### 2. Canonical trace construction

Each proposed call becomes an `AgentGuardTraceV1` containing:

- workspace, agent, deployment, and integration identity,
- user request and normalized intent text,
- proposed tool name and arguments,
- tool category, side-effect type, and declared risk level,
- prior tool sequence,
- previous output summary,
- explicit constraints,
- data-scope fields,
- retrieval text,
- execution state.

This schema is a solid foundation. It keeps raw trace facts separate from derived
features, scores, decisions, labels, and session state.

### 3. Feature extraction

`TraceFeatureBuilderV1` currently creates four groups of evidence.

#### Policy features

- whether the tool is in the task-relevant set,
- whether the tool is explicitly forbidden,
- whether confirmation is required,
- whether an explicit constraint is violated,
- whether the tool category matches the intent domain,
- whether a forbidden data scope appears in the argument summary,
- whether the action has side effects,
- whether the action is irreversible.

#### Context features

- untrusted instruction flag,
- external-link flag,
- secret-like-content flag,
- text similarity between previous output and current arguments,
- text similarity between user intent and proposed tool call.

#### Retrieval features

When Elastic is disabled, retrieval returns no evidence.

When Elastic is enabled, AgentGuard performs lexical `multi_match` search over historical
traces filtered by intent domain and tool category. Neighbor decisions or labels are
grouped as approved or intervention examples.

#### Historical statistics

The schema supports counts, transition probabilities, sequence rarity, argument-cluster
distance, historical block rate, and historical approval rate.

Most of these values are currently zero. Sequence rarity is hard-coded to `0.2` when a
tool is not considered relevant, and argument-cluster distance is hard-coded to `0.3`
when a data-scope violation is detected.

### 4. Risk scoring

`GuardScorerV1` calculates:

- intent drift,
- sequence deviation,
- argument drift,
- permission risk,
- tool-output susceptibility,
- retrieval risk,
- step risk,
- cumulative session risk.

The formulas are deterministic weighted sums. For example, step risk is:

```text
0.25 * intent drift
+ 0.15 * sequence deviation
+ 0.15 * argument drift
+ 0.20 * permission risk
+ 0.10 * tool-output susceptibility
+ 0.15 * retrieval risk
```

The weights were manually selected. They have not been fitted or calibrated against a
labeled benchmark.

### 5. Hard policy and thresholds

`DecisionPolicyV1` applies rules in this order:

1. Force block when the testing override is enabled.
2. Intervene when the tool is explicitly forbidden by the intent.
3. Block an untrusted-output-driven side effect.
4. Review a data-scope violation.
5. Block when cumulative risk is at least `0.85`.
6. Require approval when cumulative risk is at least `0.70`.
7. Review when final risk is at least `0.55`.
8. Warn when final risk is at least `0.35`.
9. Otherwise allow.

An explicitly forbidden irreversible action is blocked. A forbidden reversible action
requires approval.

### 6. Persistence and observability

The firewall persists:

- traces,
- features,
- scores,
- decisions,
- live events,
- session risk.

Local mode uses JSONL plus one JSON session-state file. Elastic mode mirrors the
governance records into dedicated indices and enables lexical precedent retrieval.

The React dashboard reads selected-agent records and exposes:

- agent definition and tools,
- live interception state,
- trace replay,
- decision memory,
- operational summaries.

## What Is Genuinely Functional


| Component                        | State                 | Notes                                                   |
| -------------------------------- | --------------------- | ------------------------------------------------------- |
| ADK pre-tool callback            | Functional            | Runs before shell and Gmail tools                       |
| Tool execution blocking          | Functional            | A block returns a synthetic response and skips the tool |
| Canonical trace schema           | Functional            | Good separation of facts and derived records            |
| Agent ownership fields           | Functional for demo   | Seeded single workspace/agent/deployment                |
| Local persistence                | Functional            | Append-only JSONL and session-state JSON                |
| Elastic indexing                 | Functional            | HTTP-based indexing and dashboard reads                 |
| Elastic precedent retrieval      | Partially functional  | Lexical retrieval, no embeddings or calibrated use      |
| Session risk accumulation        | Functional in process | Not restored into memory after process restart          |
| Selected-agent dashboard queries | Functional            | Filters traces and metrics by `agent_id`                |
| Replay and decision memory       | Functional            | Joins persisted trace, score, decision, and events      |
| Force-block test mode            | Functional            | Useful for proving enforcement                          |
| Metrics computation              | Functional scaffold   | Requires a meaningful labeled dataset                   |


## Placeholder or Weak Logic

### Intent understanding

The ADK adapter sets:

```text
normalized_intent = raw user request
task-relevant tools = the tool that the model already proposed
domain = the proposed tool's category
```

This creates circular evidence. A proposed tool usually appears relevant because the
adapter declares it relevant after seeing the proposal. The guard is not independently
deriving what tools or scopes the user authorized.

The only meaningful live negative-intent parser is a phrase list for Gmail send actions,
such as "do not send" and "draft only."

### Shell-command analysis

All `run_shell_command` calls share one broad metadata record. AgentGuard does not parse
the shell command AST or distinguish:

- `pwd` from `rm -rf`,
- reading a file from modifying it,
- local writes from network exfiltration,
- privilege escalation,
- destructive flags,
- pipes and redirects,
- encoded or obfuscated commands,
- access to secrets or sensitive paths.

This is why benign and dangerous shell commands can receive similar scores.

### Tool metadata consistency

The ADK adapter classifies `run_shell_command` as low side effect without default
confirmation. The default feature-builder registry classifies it as high risk and
confirmation-required. Because the trace metadata and feature registry are separate,
the same tool can carry inconsistent risk semantics at different pipeline stages.

### Context and prompt-injection detection

The schema has useful context flags, but the live ADK path does not currently populate
them through a real detector. Consequently, the hard rule for
`untrusted_output_plus_side_effect` is rarely reachable from genuine runtime evidence.

### Historical statistics

Transition probabilities, tool priors, sequence rarity, argument clusters, and historical
intervention rates are not computed from history. Most values are defaults or constants.

### Risk model and thresholds

The weighted scorer and thresholds are hand-authored. There is no:

- calibration dataset,
- probability calibration,
- threshold optimization,
- confidence interval,
- per-tool or per-policy threshold,
- drift monitoring,
- model version artifact beyond a string.

### Retrieval

Elastic retrieval is lexical, limited to historical records by default, and normalizes
scores relative to the best hit in each query. It does not use:

- embeddings,
- hybrid retrieval,
- cross-encoder reranking,
- policy/version compatibility filtering,
- workspace/agent ownership filtering inside the retrieval query,
- minimum evidence quality thresholds.

The last point is important for a future multi-tenant product.

### Policies

There is no real policy object loaded from storage. Thresholds and hard rules are Python
code. The dashboard displays a policy ID, but users cannot define:

- allowed tools,
- forbidden tools,
- argument constraints,
- data scopes,
- required approvals,
- environment-specific rules,
- subject or role conditions,
- time or rate limits.

### Session state durability

Session risk is written to disk, but `SessionRiskManagerV1.get()` reads only its in-memory
dictionary. A process restart loses the active cumulative state even though the JSON file
exists.

The manager is also not designed for concurrent workers updating the same session.

### Approval workflow

`require_approval` currently means "return a synthetic blocked response." There is no
durable pending action, operator authentication, expiration, approval token, or mechanism
to resume the exact suspended ADK tool call.

### Redaction and secret handling

Redaction currently checks only whether a whole string contains words such as `secret`,
`token`, or `password`. Raw arguments and output summaries can still persist credentials,
API keys, personal data, file contents, and email content.

### Evaluation

The evaluation package can replay traces and compute metrics, but all named baselines
currently return the same firewall. There is no valid comparison between:

- rule-only,
- stateless intent guard,
- trajectory-aware guard,
- retrieval-aware guard.

The repository has automated implementation tests, but not a sufficiently large,
independently labeled behavioral benchmark.

### Runtime and dashboard inconsistencies

The current agent-scoped `GET /interceptions/current` endpoint uses
`AgentLiveRuntimeService`, but the agent-scoped `/events/stream` endpoint is still wired
to `DemoRuntimeService`. The browser can therefore subscribe to a different event source
from the one used for current real ADK state.

`AgentLiveRuntimeService` polls JSONL files every 200 ms. This is acceptable for a local
demo but not a production event transport.

The old Python dashboard package under `src/agentguard/dashboard/` remains a placeholder.
The active product UI is the React application under `apps/agentguard_dashboard/`.

## Production Target

The guard should make a decision from independently derived evidence:

```text
user request
    -> intent contract extractor
    -> policy resolver

proposed tool + structured arguments
    -> tool-specific argument analyzer
    -> side-effect and data-flow classifier

prior trajectory + tool outputs
    -> provenance and injection detector
    -> sequence/statistical analyzer

historical labeled traces
    -> tenant-safe hybrid retrieval
    -> calibrated behavioral features

all evidence
    -> deterministic hard-policy engine
    -> calibrated risk model
    -> optional constrained judge for ambiguous cases
    -> allow / warn / review / require approval / block
```

Hard policy must remain authoritative. A statistical or language model must never
override an explicit deny rule.

## Phased Implementation Plan

### Phase 0: Correctness and one source of truth

Goal: make the existing demo internally consistent before changing intelligence.

Work:

- Wire agent-scoped SSE to `AgentLiveRuntimeService`.
- Remove or isolate obsolete global demo live routes from the real-agent UI.
- Build one `ToolRegistry` instance and pass it to trace construction and feature
extraction.
- Restore session risk from persisted state on startup.
- Make blocked-event production idempotent; the firewall and adapter can currently emit
separate `tool_blocked` events for one call.
- Add explicit guard/policy/version fields to every decision.
- Surface force-block and runtime mode in agent health/configuration.

Exit tests:

- A real ADK call appears through SSE without polling the page.
- One call produces one authoritative terminal execution event.
- Restarting the API/agent preserves cumulative session risk.
- Trace metadata and feature metadata agree for every registered tool.

### Phase 1: Real policy engine

Goal: replace hard-coded Python policy assumptions with explicit, testable policy data.

Introduce:

- `PolicyDefinitionV1`,
- policy assignment by workspace/agent/deployment,
- tool rules,
- argument predicates,
- allowed and forbidden data scopes,
- approval requirements,
- environment overrides,
- policy versioning and audit history.

Use a deterministic evaluator first. JSONLogic, CEL, or a small typed internal DSL are
reasonable options. Do not use an LLM to enforce explicit policy.

Exit tests:

- Policy fixtures cover allow, deny, approval, scope, and argument constraints.
- Every hard decision identifies the exact policy version and rule IDs.
- Changing a policy changes decisions without a code deployment.

### Phase 2: Intent contract extraction

Goal: derive authorization independently from the proposed tool.

Build an `IntentContractExtractor` that returns structured:

- task goal,
- requested actions,
- explicitly forbidden actions,
- permitted tools or capability classes,
- data subjects and scopes,
- destinations,
- side-effect authorization,
- confirmation language,
- uncertainty and provenance.

Use a layered approach:

1. deterministic phrase and entity extraction,
2. tool schema/capability mapping,
3. structured LLM extraction only for unresolved language,
4. strict schema validation and conservative fallback.

Cache the contract once per user turn. Do not let the proposed tool define its own
relevance.

Exit tests:

- A benchmark of paraphrases produces stable intent contracts.
- "Draft but do not send" forbids all send variants.
- Shell requests distinguish inspection, creation, modification, deletion, network, and
privilege actions.
- Extraction failure defaults to approval for side effects, not silent allow.

### Phase 3: Tool-specific argument and side-effect analysis

Goal: understand what the proposed call will actually do.

For shell commands:

- parse commands into an AST,
- classify binaries, flags, redirects, pipes, substitutions, and network endpoints,
- detect destructive operations, privilege escalation, persistence, secret access, and
exfiltration,
- normalize paths and enforce workspace/path scopes,
- identify read-only versus mutating behavior.

For Gmail:

- classify search/read/draft/send,
- validate recipients and domains,
- detect new recipients versus user-authorized recipients,
- identify attachment and sensitive-content risk.

Use a plugin interface so every tool family provides:

- normalized action,
- resource set,
- side effects,
- reversibility,
- sensitivity,
- required capabilities.

Exit tests:

- `pwd` and `rm -rf` produce materially different evidence and decisions.
- Redirects, pipes, command substitution, and encoded commands cannot evade policy.
- Gmail send cannot bypass controls through a different send-tool alias.

### Phase 4: Provenance, prompt injection, and data-flow controls

Goal: detect when untrusted tool output causes a dangerous next action.

Track provenance for:

- user instructions,
- system/developer instructions,
- model-generated text,
- tool outputs,
- retrieved external content.

Add detectors for:

- instruction-like text in untrusted content,
- secret-like values,
- external links and destinations,
- output-to-argument copying,
- cross-domain data movement.

The guard should answer: "Did an untrusted email or webpage cause the agent to execute a
side effect that the user did not authorize?"

Exit tests:

- Indirect prompt-injection scenarios block or require approval.
- Benign quoted instructions do not create excessive false positives.
- Sensitive data movement across tools is visible in the decision evidence.

### Phase 5: Historical features and retrieval

Goal: make trajectory-conditioned evidence real.

Implement:

- per-agent and per-tool priors,
- transition probabilities,
- n-gram or sequence-model rarity,
- argument-distribution models,
- intervention rates,
- hybrid lexical and vector retrieval,
- tenant and policy-version filters,
- minimum similarity/evidence thresholds.

Retrieval should prefer human labels over previous model decisions to avoid feedback
loops.

Exit tests:

- Retrieved precedents are from the correct workspace/agent policy boundary.
- Known anomalous sequences score higher than common valid sequences.
- Removing retrieval evidence produces a measurable benchmark difference.

### Phase 6: Calibrated scoring and decisioning

Goal: replace manual weights with evidence-backed scores.

Start with interpretable models:

- logistic regression,
- gradient-boosted trees,
- monotonic models for safety-critical features.

Train component models or one final intervention model using labeled traces. Calibrate
outputs with isotonic regression or Platt scaling. Keep hard-policy decisions separate.

Thresholds should be selected from explicit objectives:

- harmful-call recall,
- false-intervention rate,
- approval workload,
- per-tool cost of error.

Exit tests:

- Separate validation and test metrics.
- Baseline comparisons are genuinely distinct.
- Thresholds and model artifacts are versioned and reproducible.
- A model card documents dataset coverage and known failure domains.

### Phase 7: Durable approval and execution continuation

Goal: turn `require_approval` into a real workflow.

Persist a pending action containing:

- trace and call IDs,
- normalized arguments,
- argument hash,
- policy version,
- expiration,
- requester identity,
- required approver role.

On approval:

- verify the call and argument hash have not changed,
- issue a short-lived single-use execution authorization,
- resume or safely re-dispatch the exact tool call,
- record approver, time, reason, and outcome.

Exit tests:

- Approving one call cannot authorize another.
- Expired or modified calls cannot execute.
- Reject, timeout, and abort are auditable terminal states.

### Phase 8: Production storage and event architecture

Goal: remove local-process assumptions.

Replace JSONL polling with:

- durable event ingestion,
- idempotency keys,
- optimistic concurrency for session state,
- a queue or stream for live events,
- lifecycle retention policies,
- encrypted sensitive fields,
- robust redaction before persistence.

Elastic remains useful for search and analytics but should not be the sole transactional
authority for approvals or execution authorization.

### Phase 9: Evaluation, rollout, and monitoring

Goal: prove the guard works and remains safe after deployment.

Build:

- labeled benign and harmful tool-call datasets,
- adversarial prompt-injection suites,
- unseen-agent and unseen-domain splits,
- shadow mode,
- policy-only fallback mode,
- decision disagreement review,
- false-positive and false-negative monitoring,
- model/policy drift alerts.

Promotion gates should require target harmful-call recall and maximum false-intervention
rates, not only passing unit tests.

## Recommended Immediate Build Order

The next implementation sequence should be:

1. Fix SSE source, event duplication, metadata consistency, and session-state restore.
2. Define `PolicyDefinitionV1` and implement deterministic policy evaluation.
3. Implement shell-command parsing and classification.
4. Implement independent intent-contract extraction.
5. Add prompt-injection/provenance evidence.
6. Build a labeled benchmark and genuinely distinct baselines.
7. Implement real historical statistics and tenant-safe hybrid retrieval.
8. Calibrate the scorer and thresholds.
9. Build durable approval continuation.

This order produces useful security improvements early. It does not depend on training a
large model before the guard can enforce meaningful rules.

## Definition of a Non-Placeholder AgentGuard

AgentGuard should no longer be described as placeholder logic when all of the following
are true:

- intent authorization is derived independently of the proposed tool,
- tool arguments are analyzed by tool-specific parsers,
- explicit policies are data-driven and versioned,
- untrusted-output provenance is populated at runtime,
- historical statistics are computed from real history,
- retrieval is tenant-safe and benchmarked,
- risk scores are calibrated on held-out labels,
- approval can securely resume the exact pending action,
- session state is durable and concurrency-safe,
- evaluation proves improvement over distinct baselines,
- production decisions expose complete, reproducible evidence.

