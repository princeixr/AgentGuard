# AgentGuard Realistic Demo Scope

Last updated: 2026-06-07

The detailed target firewall design, policy lifecycle, tier contracts, migration plan,
and decision precedence are defined in
[Guard_architecture.md](Guard_architecture.md).

## Product Claim

For the current demo, AgentGuard should claim:

> AgentGuard is a policy-driven runtime firewall for Google ADK tool calls. It
> intercepts calls before execution, classifies supported actions, enforces explicit
> rules, and records the decision and evidence for live monitoring and replay.

It should not claim:

- general malicious-agent detection,
- calibrated anomaly probabilities,
- comprehensive prompt-injection prevention,
- learned behavioral baselines,
- support for arbitrary tools without configuration,
- production-grade human approval continuation.

## Features We Should Definitely Implement

### 1. One authoritative live event path

Every real ADK proposal, decision, and execution outcome must reach the selected-agent
dashboard through the same event service.

Required behavior:

- remove the real-agent UI dependency on the deterministic demo event broker,
- emit one authoritative terminal event per call,
- preserve selected `agent_id`, session, trace, and call identity,
- restore session state after restart.

Why it matters:

Without this, the dashboard cannot reliably prove what the guard actually enforced.

### 2. Versioned, data-driven policy rules

Replace Python-only decision assumptions with a small policy document loaded from JSON
or YAML.

The demo policy only needs:

- allowed and denied tools,
- actions that always require approval,
- permitted filesystem roots,
- forbidden filesystem roots,
- permitted email recipient domains,
- destructive shell actions that must be blocked,
- network and privilege-related shell actions that must be blocked.

Every decision must record:

- policy ID and version,
- rule IDs that matched,
- final enforcement action,
- human-readable explanation.

Why it matters:

This creates a real security control that is deterministic, inspectable, and changeable
without modifying the scorer.

### 3. Limited but real tool-action classification

Implement classifiers only for the tools used by the demo.

#### Shell

Classify a command as one or more of:

- read or inspect,
- create or write,
- delete,
- execute,
- network access,
- privilege escalation,
- sensitive-path access,
- unknown or unsupported.

Use shell parsing where practical. If parsing fails or the command uses unsupported
syntax, side-effecting calls should require approval or be blocked according to policy.

#### Gmail

Classify:

- search,
- read,
- draft,
- send,
- send draft,
- recipient domains.

Why it matters:

The current guard treats shell commands too uniformly. A useful guard must distinguish
`pwd` from file deletion, network exfiltration, and privilege escalation.

### 4. Deterministic intent constraints

Implement a narrow intent parser for the demo's supported controls:

- `do not send`,
- `draft only`,
- explicit request to send,
- inspect/read-only requests,
- create/write requests,
- delete requests,
- mentioned paths,
- mentioned recipients and domains.

The proposed tool must not define its own relevance. The intent contract should be
created once from the user message and then compared with each proposed action.

If intent is ambiguous:

- allow clearly read-only operations,
- require approval for reversible side effects,
- block destructive or policy-forbidden actions.

Why it matters:

This fixes the largest logical weakness without requiring a trained model.

### 5. Enforcement and audit evidence

The ADK callback must:

- execute `allow`,
- execute and record `warn`,
- stop `require_approval`,
- always stop `block`,
- never execute a changed call under an earlier decision.

The dashboard must show:

- normalized action,
- matched policy rules,
- intent constraints,
- risk indicators as heuristic evidence, not probability,
- execution outcome,
- trace and policy versions.

Why it matters:

The demo should prove enforcement, not only produce a score.

### 6. A repeatable verification suite

Create a checked-in scenario matrix with expected decisions. This is more valuable for
the demo than adding an LLM judge or an uncalibrated anomaly model.

The suite should cover:

- benign shell inspection,
- permitted file creation,
- forbidden deletion,
- sensitive-path access,
- network command,
- privilege escalation,
- Gmail search/read,
- Gmail draft without send,
- send despite `do not send`,
- explicitly requested send,
- unknown tool,
- malformed or unsupported shell syntax,
- force-block mode.

## Features to Defer

These are valuable but should not be part of the committed demo scope:

- trained anomaly model,
- calibrated risk probabilities,
- vector or hybrid retrieval,
- learned sequence baselines,
- general prompt-injection detection,
- LLM-as-judge,
- arbitrary tool onboarding,
- multi-tenant authentication and RBAC,
- secure pause-and-resume approval execution,
- distributed event queues,
- production secret-management and retention controls.

Existing Elastic precedent retrieval can remain visible as experimental evidence, but it
should not be required for enforcement.

## Verification Strategy

### Layer 1: Classifier unit tests

Each supported action must have table-driven tests.

Example shell expectations:

| Command | Classification |
| --- | --- |
| `pwd` | read/inspect |
| `ls -la` | read/inspect |
| `cat README.md` | read + path access |
| `touch notes.txt` | create/write |
| `rm notes.txt` | delete |
| `curl https://example.com` | network |
| `sudo whoami` | privilege escalation |
| `cat ~/.ssh/id_rsa` | sensitive-path access |

Pass condition:

- all supported examples classify correctly,
- unsupported syntax produces `unknown`, not a silent low-risk result.

### Layer 2: Policy-engine unit tests

Given a normalized action and policy, test the exact rule and decision.

Examples:

| Action | Expected result |
| --- | --- |
| Read repository file inside allowed root | `allow` |
| Write inside allowed temporary root | `allow` or `require_approval`, per policy |
| Delete any file | `block` |
| Read `~/.ssh` | `block` |
| Use network command | `block` |
| Gmail send to approved domain with explicit request | `require_approval` |
| Gmail send after `do not send` | `block` |

Pass condition:

- every decision contains the expected policy ID, version, and rule ID,
- changing policy data changes the result without code changes.

### Layer 3: Intent-contract tests

Use paraphrase sets rather than one exact phrase.

Examples:

```text
Draft a response but don't send it.
Prepare a reply only.
Write the email and leave it in drafts.
```

All must forbid Gmail send actions.

Pass condition:

- supported constraints are extracted consistently,
- ambiguous side-effect requests never silently become `allow`.

### Layer 4: Firewall integration tests

Run canonical traces through:

```text
trace -> classifier -> policy -> decision -> persistence
```

Verify:

- trace, evidence, decision, and event share the same IDs,
- exactly one terminal event is produced,
- blocked calls have no executed event,
- session state survives recreation of the guard service.

### Layer 5: Google ADK callback tests

Use a spy tool that records whether it was called.

Verify:

- allowed proposal invokes the tool once,
- blocked proposal invokes the tool zero times,
- approval-required proposal invokes the tool zero times,
- force-block invokes the tool zero times,
- callback response contains the trace ID and explanation.

### Layer 6: API and SSE tests

Start the FastAPI app against a temporary trace store.

Verify:

- selected agent receives only its own events,
- SSE receives real ADK events in order,
- `/interceptions/current` and SSE report the same trace and status,
- replay shows the same decision and execution outcome,
- operations counts reconcile with persisted decisions.

### Layer 7: Browser smoke test

Run four scripted scenarios from Agent Details:

1. `pwd` results in `ALLOW` and execution output.
2. A forbidden delete results in `BLOCK` and no deletion.
3. Gmail draft results in `ALLOW`.
4. Gmail send after `do not send` results in `BLOCK`.

For each scenario, verify Live Interception, Trace Replay, Decision Memory, and Operations
show the same outcome.

### Layer 8: Safety regression gate

Maintain a checked-in JSONL scenario corpus:

```text
scenario ID
user request
proposed tool
arguments
expected normalized action
expected decision
expected rule IDs
```

CI fails when:

- a previously blocked case becomes allowed,
- an allowed read-only case becomes blocked unexpectedly,
- decision evidence is missing,
- execution occurs after a block.

## Realistic Delivery Sequence

Assuming one engineer familiar with this repository:

### Milestone 1: Runtime correctness

Estimated effort: 1-2 working days.

- real ADK SSE wiring,
- terminal-event deduplication,
- metadata consistency,
- session-state restore,
- integration tests.

### Milestone 2: Policy engine

Estimated effort: 2-3 working days.

- policy schema and loader,
- deterministic evaluator,
- rule evidence,
- default demo policy,
- policy tests.

### Milestone 3: Shell and Gmail classification

Estimated effort: 3-5 working days.

- supported action models,
- shell and Gmail classifiers,
- conservative unknown handling,
- classifier and policy integration tests.

### Milestone 4: Intent constraints and end-to-end validation

Estimated effort: 2-4 working days.

- narrow deterministic intent parser,
- scenario corpus,
- ADK/API/SSE tests,
- browser verification checklist,
- dashboard evidence updates.

Total realistic implementation estimate: approximately 8-14 focused working days,
excluding Gmail OAuth/Docker environment problems and significant UI redesign.

## Demo Acceptance Criteria

The scoped demo is complete when:

1. The guard independently classifies the supported user intent and proposed action.
2. A versioned policy produces the final enforcement decision.
3. Benign inspection executes.
4. Forbidden destructive, sensitive, or network actions do not execute.
5. Gmail send cannot bypass a `do not send` constraint.
6. Every outcome is visible consistently across live interception, replay, memory, and
   operations.
7. The scenario regression suite passes in CI.
8. The UI labels heuristic risk as supporting evidence rather than a calibrated threat
   probability.
