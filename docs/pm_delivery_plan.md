# AgentGuard Product & Delivery Plan v0.1

## Owner

**Product Manager — Delivery + Coordination**

Primary responsibility: keep the project moving toward a finished hackathon artifact by managing scope, milestones, dependencies, integration, documentation, and demo readiness.

This document inherits from `docs/shared_contract.md`.

---

## PM Mission

The PM is not a corporate process layer.

The PM is the operating system of the team.

Their job is to prevent:

1. scope expansion,
2. late integration failure,
3. unclear ownership,
4. weak demo narrative,
5. missed deadlines,
6. documentation drift.

---

## Project North Star

AgentGuard should be presented as:

```text
Trajectory-aware runtime governance for Google ADK agents.
```

The product/research claim:

```text
AgentGuard detects intent-relative and trajectory-level tool-use failures that stateless action-level guards miss.
```

Do not let the project become:

```text
another generic AI firewall
```

or:

```text
a broad agent security platform
```

---

## Team Ownership

| Track | Owner | PM Checks |
|---|---|---|
| Runtime + Agent Infrastructure | Developer 1 | Can sessions run and emit valid traces? |
| Governance + Retrieval Engine | Developer 2 | Can traces produce explainable verdicts? |
| Evaluation + Dashboard | Developer 3 | Can we prove AgentGuard beats baselines? |
| Delivery + Coordination | PM | Is the whole project demo-ready by June 4? |

---

## Milestone Timeline

### May 27 — Architecture Freeze

PM deliverables:

- confirm shared contract accepted,
- confirm runtime strategy: Google ADK primary, mock fallback,
- assign owners,
- create task board,
- create integration checklist.

Exit criteria:

```text
No one is unclear about what they own.
No one starts coding outside the agreed architecture.
```

---

### May 28–29 — Core Infrastructure

PM tracks:

| Owner | Expected Output |
|---|---|
| Developer 1 | runtime skeleton, mock tools, trace emission |
| Developer 2 | static guard, decision policy skeleton |
| Developer 3 | scenario files, label schema validation, metric skeleton |

Integration checkpoint:

```text
One scenario should run through runtime → trace → guard → decision.
```

---

### May 30–31 — Failure Scenario Development

PM tracks:

| Demo | Owner Coordination |
|---|---|
| Draft vs Send | Dev 1 runtime + Dev 2 policy + Dev 3 labels |
| File Scope Creep | Dev 1 tools + Dev 2 scoring + Dev 3 scenario |
| Prompt Injection | Dev 1 tool output + Dev 2 susceptibility score + Dev 3 dashboard replay |

Exit criteria:

```text
At least three end-to-end trajectories exist.
```

---

### June 1 — Baseline Evaluation

PM tracks:

- rule-only baseline complete,
- stateless intent baseline complete,
- full AgentGuard complete,
- labels available,
- metrics computed,
- failure cases reviewed.

Exit criteria:

```text
Baseline comparison table has real computed values.
```

---

### June 2 — Demo Engineering

PM tracks:

- dashboard views,
- demo script,
- screenshots,
- backup recording,
- narrative alignment.

Exit criteria:

```text
A non-technical judge can understand why AgentGuard is different within 60 seconds.
```

---

### June 3–4 — Stabilization Buffer

PM tracks:

- bug fixes only,
- no new features,
- presentation rehearsal,
- demo fallback path,
- final README cleanup,
- Devpost assets.

Exit criteria:

```text
Final demo can be run twice in a row without manual rescue.
```

---

## Daily Sync Format

Daily sync should be 20 minutes.

Each person answers:

```text
1. What did I finish?
2. What is blocked?
3. What needs integration today?
4. What will be demo-visible by tonight?
```

Do not use daily sync for long architecture debates.

Architecture debates go into research review.

---

## Twice-Weekly Research Review

Purpose:

- validate benchmark quality,
- challenge claims,
- inspect failure cases,
- ensure narrative consistency.

Questions to ask:

```text
1. What does this prove?
2. What does it not prove?
3. Would a stateless guard catch this too?
4. Are we cherry-picking?
5. Is this demo understandable?
6. Are claims stronger than evidence?
```

---

## Scope Control Rules

### Allowed

- Google ADK primary demo,
- mock tools,
- deterministic scenarios,
- local JSONL traces,
- simple retrieval,
- hand-tuned scoring,
- three polished demos.

### Not Allowed Without Team Approval

- new domains,
- real Gmail/calendar credentials,
- fine-tuned models,
- complex multi-agent orchestration,
- production auth,
- enterprise dashboard features,
- additional runtime frameworks beyond adapter placeholders.

---

## Integration Checklist

PM should verify daily:

```text
[ ] shared models still import correctly
[ ] runtime emits valid RawTraceRecord
[ ] governance consumes RawTraceRecord
[ ] governance emits GuardDecision
[ ] evaluation can load traces and labels
[ ] dashboard can read stored outputs
[ ] tests pass
[ ] no one bypassed shared interfaces
```

---

## Demo Narrative

The demo should follow this structure:

### 1. Problem

AI agents can make tool calls that are safe in isolation but wrong in trajectory context.

### 2. Example

User asks for a draft. Agent tries to send.

### 3. Baseline Failure

Stateless guard sees:

```text
gmail_send with valid args
```

### 4. AgentGuard Reasoning

AgentGuard sees:

```text
user asked for draft
prior steps were search/read
send exceeds requested autonomy
similar blocked traces exist
```

### 5. Result

AgentGuard returns:

```text
require_approval or block
```

### 6. Generalization

Same architecture applies to file scope creep and prompt injection from tool output.

---

## Devpost Deliverables

PM owns the checklist:

```text
[ ] project title
[ ] short description
[ ] long description
[ ] problem statement
[ ] how it uses Google ADK/Gemini
[ ] architecture diagram
[ ] demo video
[ ] screenshots
[ ] GitHub repo
[ ] setup instructions
[ ] benchmark/evaluation summary
[ ] limitations section
[ ] future work
```

---

## README Requirements

PM should ensure README includes:

```text
1. What AgentGuard is
2. Why trajectory context matters
3. How to run demo
4. How to run benchmark
5. How to view dashboard
6. Architecture overview
7. Google ADK usage
8. Known limitations
```

---

## Risk Register

| Risk | Severity | Mitigation |
|---|---:|---|
| Google ADK integration delay | High | MockRuntimeAdapter fallback |
| Weak evaluation | High | Developer 3 owns metrics + labels early |
| Scope creep | High | PM enforces freeze |
| Late integration | High | Daily integration checkpoint |
| Demo instability | High | backup replay mode + recording |
| Overclaiming novelty | Medium | keep claims evidence-bound |
| Retrieval not impressive | Medium | use retrieval as explanation support, not sole claim |

---

## PM Milestones

### Milestone P1 — Project Board

Deliver:

- task board,
- owners,
- deadlines,
- integration dependencies.

### Milestone P2 — Demo Script v0

Deliver:

- 3-demo script,
- judge-facing explanation,
- screenshot plan.

### Milestone P3 — Devpost Draft

Deliver:

- draft project description,
- Google ADK usage section,
- architecture summary.

### Milestone P4 — Final Readiness

Deliver:

- final checklist complete,
- demo rehearsed,
- fallback demo ready,
- README clean.

---

## Coding Agent Prompt for PM/Docs Track

```text
You are supporting the Product + Delivery track for AgentGuard.

Read docs/shared_contract.md and docs/pm_delivery_plan.md first.

Generate operational project-management artifacts only. Do not implement runtime, governance, or evaluation logic.

Tasks:
1. Create a milestone checklist.
2. Create a daily integration checklist.
3. Create a Devpost submission checklist.
4. Create a demo script outline for three demos.
5. Create a README outline.
6. Create a risk register.
7. Ensure all language positions Google ADK as the primary hackathon runtime.
8. Avoid overclaiming production readiness or universal agent safety.

The PM materials should help the team finish a credible hackathon demo by June 4.
```

---

## Non-Negotiables

1. No new scope after freeze.
2. Daily integration is mandatory.
3. Demo must be understandable to non-specialists.
4. Metrics must be evidence-bound.
5. Google ADK must be visible in the hackathon story.
6. Fallback demo must exist.
