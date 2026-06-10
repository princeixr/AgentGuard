# AgentGuardFirewallV2 Development Plan

Status: implementation plan
Last updated: 2026-06-07
Architecture source: [Guard_architecture.md](Guard_architecture.md)

## 1. Development Strategy

AgentGuardFirewallV2 will be developed beside V1 and introduced incrementally.

We will not remove the working Google ADK interception, persistence, API, or dashboard
path. V2 will reuse those boundaries while replacing the governance logic behind them.

```text
Google ADK callbacks
        |
        +-- FirewallV1: existing enforcement during early development
        |
        +-- FirewallV2: shadow evaluation and evidence
```

After V2 passes the agreed scenarios:

```text
Google ADK callbacks
        |
        +-- FirewallV2: enforcement
        |
        +-- FirewallV1: optional comparison, then removal
```

### Operating modes

Introduce one configuration value:

```env
AGENTGUARD_FIREWALL_MODE=v1
```

Supported values will be:

| Mode | Behavior |
| --- | --- |
| `v1` | V1 evaluates and enforces |
| `v2_shadow` | V1 enforces; V2 evaluates and records without affecting execution |
| `v2` | V2 evaluates and enforces |

`v2_shadow` is essential. It lets us inspect V2 through the UI before trusting it with
execution.

### Development rule

Every phase must finish with:

1. Backend unit tests.
2. An API integration test.
3. A visible UI result.
4. A short manual scenario checklist.
5. User confirmation before moving to the next behavior-changing phase.

## 2. UI Development Surface

We will expose V2 progress through the current dashboard rather than build a separate
debug application.

### Agent Details

This page will show configuration and setup:

- active firewall mode,
- V1/V2 version,
- selected policy and version,
- tool descriptors,
- capabilities,
- normalizer assignments,
- supported and unsupported tools,
- policy preview.

### Live Interception

This page will show the evaluation of the current call:

- raw tool proposal,
- normalized action,
- extracted intent contract,
- effective policy,
- evaluation plan,
- Tier 1 result,
- Tier 2 result,
- Tier 3 result,
- final decision precedence,
- execution outcome.

Components that are not implemented yet will be labeled `Not run` or `Unavailable`,
not shown as successful.

### Trace Replay

This page will show the complete persisted V2 timeline:

```text
proposal
intent
normalization
policy resolution
tier results
final decision
execution
```

### Policies

The existing Policies navigation item will eventually open a real page containing:

- active policy summary,
- important guided controls,
- generated YAML/JSON preview,
- validation results,
- policy version history.

For early phases, policy details can first appear on Agent Details.

## 3. Record Compatibility

V2 will create new records rather than overload incomplete V1 fields.

Initial V2 records:

- `ToolDescriptorV1`
- `PolicyDefinitionV1`
- `EffectivePolicyV1`
- `IntentContractV2`
- `NormalizedActionV1`
- `EvaluationPlanV1`
- `TierResultV1`
- `GuardDecisionV2`

Every V2 record references the existing:

- `trace_id`,
- `session_id`,
- `agent_id`,
- `workspace_id`,
- `deployment_id`.

V1 traces remain readable. The dashboard query layer will return optional V2 evidence
when it exists.

## 4. Phase 0: Runtime and UI Observability Correctness

### Goal

Establish a trustworthy path before adding new security logic.

### Backend work

- Fix selected-agent SSE to use `AgentLiveRuntimeService`.
- Ensure `/interceptions/current` and `/events/stream` use the same source.
- Deduplicate terminal `tool_blocked` events.
- Add explicit `guard_version` and `firewall_mode` to API responses.
- Persist and restore session state after restart.
- Ensure one proposal produces one final execution outcome.

### UI work

Agent Details:

- show `Firewall: V1`,
- show current firewall mode,
- show trace namespace.

Live Interception:

- show event source as `Google ADK runtime`,
- show trace ID, call ID, and guard version,
- show a clear execution outcome.

### Automated verification

- SSE receives real ADK events.
- Current interception and SSE reference the same trace.
- Exactly one terminal event exists per call.
- Restarting services preserves the latest session state.
- Agent filtering prevents cross-agent events.

### Manual UI test

Prompt:

```text
Show me the current directory.
```

Expected:

- Agent Details starts the real ADK run.
- Live Interception updates without page refresh.
- Trace Replay shows one shell call.
- The trace ID and outcome agree across pages.

### Exit gate

Do not begin V2 security logic until the live event path is reliable.

## 5. Phase 1: V2 Skeleton and Shadow Mode

### Goal

Create the V2 orchestration contract without changing execution decisions.

### Backend work

Create:

```text
src/agentguard/firewall_v2/
    engine.py
    models.py
    router.py
    combiner.py
```

`AgentGuardFirewallV2.evaluate()` initially:

1. accepts the canonical proposal,
2. creates an evaluation ID,
3. records planned stages,
4. returns an `observe_only` result,
5. never changes V1 enforcement.

Add `AGENTGUARD_FIREWALL_MODE`.

In `v2_shadow`:

- V1 continues to enforce,
- V2 records its evaluation,
- the dashboard displays both decisions.

### UI work

Agent Details:

- firewall mode selector is display-only initially,
- V1 and V2 version information.

Live Interception:

- add a `V2 Shadow Evaluation` section,
- show evaluation status and stages,
- compare `Enforced V1 decision` with `V2 shadow recommendation`.

Trace Replay:

- show whether V2 evidence exists for each step.

### Automated verification

- V2 failure cannot prevent V1 execution in shadow mode.
- V2 records are tied to the correct trace.
- V1-only historical traces remain readable.
- Mode parsing rejects unsupported values.

### Manual UI tests

Run:

```text
Show me the current directory.
Create a file called v2-shadow-test.txt.
```

Expected:

- V1 behavior remains unchanged.
- Each call has a visible V2 shadow evaluation.
- V2 is explicitly marked as non-enforcing.

### Exit gate

The user can see V2 records without any execution behavior changing.

## 6. Phase 2: Tool Descriptors and Capability Registry

### Goal

Describe the selected agent's tools using one authoritative capability model.

### Backend work

Create:

```text
src/agentguard/firewall_v2/tools/
    models.py
    registry.py
    descriptor_loader.py
```

Implement descriptors for:

- `run_shell_command`,
- Gmail search,
- Gmail read,
- Gmail draft,
- Gmail send,
- Gmail send draft.

Each descriptor records:

- tool ID and provider,
- capability families,
- side effect,
- reversibility,
- impact,
- argument roles,
- assigned normalizer,
- default tier routing.

Remove the behavioral inconsistency between ADK metadata and the default V1 registry for
the supported tools. During migration, V1 may consume the new registry through an
adapter.

### UI work

Agent Details Tool Registry:

- replace category-only display with capabilities,
- show impact and reversibility,
- show assigned normalizer,
- mark inferred versus user-reviewed metadata,
- mark unsupported tools.

### Automated verification

- Every enabled demo tool has one descriptor.
- Tool aliases map to the expected capability.
- Unknown tools receive conservative metadata.
- ADK trace construction and V2 use the same descriptor.

### Manual UI test

Open Agent Details.

Expected:

```text
run_shell_command
Capabilities: dynamic.shell
Normalizer: shell_v1
Impact: dynamic

gmail_send_email
Capabilities: email.send
Normalizer: gmail_v1
Impact: high
Reversible: no
```

### Exit gate

The user can inspect exactly what AgentGuard believes each tool can do.

## 7. Phase 3: Versioned Policy Foundation

### Goal

Load and display a real policy document without using it for enforcement yet.

### Backend work

Create:

```text
src/agentguard/firewall_v2/policy/
    models.py
    loader.py
    validator.py
    resolver.py
    evaluator.py
```

Add:

```text
policies/google_adk_demo_v1.yaml
```

Implement:

- schema validation,
- immutable policy ID and version,
- scope validation,
- defaults and failure behavior,
- deterministic rule matching,
- effective policy hash,
- agent/deployment policy resolution.

The first policy covers:

- allowed tools and capabilities,
- unknown-tool behavior,
- filesystem roots,
- deletion,
- shell network access,
- privilege escalation,
- Gmail read/draft,
- Gmail send,
- permitted recipient domains.

### API work

Add:

```text
GET /api/v1/agents/{agent_id}/policy
POST /api/v1/agents/{agent_id}/policy/validate
```

Publishing/editing can remain file-based in this phase.

### UI work

Agent Details:

- active policy ID,
- version,
- validation status,
- effective policy hash,
- summarized rules.

Policies page:

- guided read-only controls,
- raw YAML preview,
- rule table,
- validation result.

### Automated verification

- Valid policy loads.
- Invalid policy fails startup or activation clearly.
- Rule conflicts resolve to the most restrictive effect.
- Changing YAML changes evaluation results without Python changes.
- Policy ownership matches the selected agent/deployment.

### Manual UI test

1. View policy version `1.0.0`.
2. Change one demo policy value, such as the permitted recipient domain.
3. Restart or reload policy.
4. Verify the UI shows the updated version/hash.

At this phase, policy matching is visible but V1 still enforces.

### Exit gate

The policy displayed in the UI resolves to a real validated document.

## 8. Phase 4: Action Normalization

### Goal

Translate every supported tool proposal into a canonical action before policy or scoring.

### Backend work

Create:

```text
src/agentguard/firewall_v2/tools/normalizers/
    shell.py
    gmail.py
```

Shell v1 supports and classifies:

- inspect/read,
- create/write,
- delete,
- execute,
- network,
- privilege escalation,
- package installation,
- process control,
- sensitive paths,
- redirects,
- pipelines,
- command substitution,
- unknown syntax.

Gmail v1 classifies:

- search,
- read,
- draft,
- send,
- send draft,
- recipients and domains,
- attachments,
- external destinations,
- basic sensitive-content indicators.

Persist `NormalizedActionV1`.

Unknown or unsupported behavior is explicit and includes parser status.

### UI work

Live Interception:

- add `Normalized Action`,
- show capabilities,
- resources and destinations,
- action flags,
- parser name/version/status.

Trace Replay:

- each tool step can expand to show the normalized action.

Agent Details:

- show normalizer support and version for each tool.

### Automated verification

Table-driven cases:

```text
pwd                         -> filesystem.inspect
cat README.md               -> filesystem.read
touch notes.txt             -> filesystem.write
rm notes.txt                -> filesystem.delete
curl example.com            -> network.request
sudo whoami                 -> privilege escalation
cat ~/.ssh/id_rsa           -> sensitive path
gmail_draft_email           -> email.draft
gmail_send_email            -> email.send
```

Unsupported syntax must not be classified as harmless.

### Manual UI tests

Run these separately:

```text
Show me the current directory.
Create a file called normalizer-test.txt.
Delete normalizer-test.txt.
Use curl to fetch https://example.com.
```

Expected:

- each trace shows a materially different normalized action,
- no enforcement change yet in shadow mode,
- unsupported behavior is visibly marked.

### Exit gate

The user agrees that the displayed action accurately represents each supported tool call.

## 9. Phase 5: Intent Contract

### Goal

Extract what the user authorized once per turn, independently of the proposed tool.

### Backend work

Create:

```text
src/agentguard/intent/
    models.py
    deterministic.py
    resolver.py
```

Implement deterministic extraction for:

- inspect/read,
- create/write,
- delete,
- email search/read,
- draft,
- send,
- `do not send`,
- `draft only`,
- paths,
- recipients and domains.

Persist one `IntentContractV2` per ADK user turn.

Every proposal from the turn references the same intent ID.

Optional structured LLM extraction is deferred until deterministic extraction is visible
and stable.

### UI work

Live Interception:

- replace raw `Authorized intent` display with structured capabilities,
- show requested and forbidden actions,
- show resources and destinations,
- show extraction method and status,
- preserve the raw user instruction.

Trace Replay:

- show one intent contract associated with all steps in the turn.

### Automated verification

Paraphrase groups:

```text
Draft it but do not send.
Prepare a reply only.
Leave it in drafts.
```

All forbid `email.send`.

Verify that tool proposals do not change the extracted contract.

### Manual UI tests

Run:

```text
Find the latest budget email and draft a reply. Do not send it.
```

Expected intent:

```text
Requested: email.search, email.read, email.draft
Forbidden: email.send
```

Any Gmail tools proposed during that turn reference one intent contract.

### Exit gate

The displayed intent remains stable and matches the user's instruction.

## 10. Phase 6: Tier 1 Shadow Evaluation

### Goal

Evaluate real deterministic policy rules without enforcing them yet.

### Backend work

Implement:

- platform baseline checks,
- policy rule evaluation,
- matched-rule evidence,
- deterministic fallback behavior,
- Tier 1 result persistence.

Tier 1 receives:

- normalized action,
- intent contract,
- effective policy,
- tool descriptor,
- session context.

V1 still enforces in `v2_shadow`.

### UI work

Live Interception:

- add a Tier 1 card,
- show checks performed,
- matched policy rules,
- recommendation,
- explanation,
- latency.

Agent Details test results:

- show V1 enforced result,
- show V2 Tier 1 recommendation,
- highlight disagreement.

Trace Replay:

- show policy version and Tier 1 rule IDs per step.

### Automated verification

Tier 1 scenarios:

- permitted inspection -> allow,
- permitted local write -> policy-defined result,
- deletion -> block,
- sensitive path -> block,
- shell network -> block,
- privilege escalation -> block,
- Gmail draft -> allow,
- Gmail send after `do not send` -> block,
- explicit Gmail send -> require approval.

### Manual UI tests

Run:

```text
Show me the current directory.
Delete a temporary file.
Read ~/.ssh/id_rsa.
Find an email and draft a reply. Do not send it.
```

Expected:

- V2 recommendations and rules are visible,
- V1 still controls execution,
- disagreements are recorded for review.

### Exit gate

Review every disagreement. Tier 1 must pass the checked-in scenario matrix before it can
enforce.

## 11. Phase 7: Tier 1 Enforcement

### Goal

Make V2 Tier 1 the active guard for supported deterministic cases.

### Backend work

Switch to:

```env
AGENTGUARD_FIREWALL_MODE=v2
```

At this phase:

- Tier 1 can allow, warn, require approval, or block.
- Calls routed to unfinished Tier 2 or Tier 3 use policy fallback.
- No V1 score may override V2 policy.
- Force-block remains available as a testing override.

### UI work

Live Interception:

- remove shadow labeling for Tier 1,
- show `Enforced by FirewallV2`,
- clearly show whether the tool executed.

Operations:

- add V2 policy intervention counts,
- add unknown/parser-failure counts.

### Automated verification

Use spy tools and filesystem assertions:

- allowed command executes once,
- blocked command executes zero times,
- blocked file is not removed,
- sensitive file content is not returned,
- approval-required action executes zero times,
- exact rule IDs are persisted.

### Manual UI tests

1. `pwd` should execute.
2. File deletion should be blocked.
3. `curl` should be blocked.
4. Gmail draft should execute.
5. Gmail send with `do not send` should be blocked.

Verify all four dashboard pages agree.

### Exit gate

Tier 1 is now a useful, independently testable AgentGuard product.

## 12. Phase 8: Guided Policy Controls

### Goal

Let the user change important policy values without manually editing YAML.

### Backend work

Add a draft policy service:

- load active policy,
- create editable draft,
- validate draft,
- preview decisions against scenarios,
- publish a new immutable version.

For the demo, editable fields are limited to:

- filesystem mode,
- allowed roots,
- file deletion,
- shell network,
- privilege escalation,
- Gmail send behavior,
- allowed recipient domains,
- unknown-action fallback.

### UI work

Policies page:

- guided controls,
- generated YAML preview,
- validation errors,
- scenario impact preview,
- publish version button,
- version history.

### Automated verification

- Publishing creates a new version.
- Previous versions remain readable.
- Invalid policy cannot activate.
- Preview does not affect runtime.
- Active policy change alters the next call's decision.

### Manual UI test

1. Set file deletion from `block` to `require approval`.
2. Preview the delete scenario.
3. Publish policy `1.1.0`.
4. Run the scenario.
5. Confirm replay references `1.1.0`.

### Exit gate

The user can safely modify central deterministic guardrails through the UI.

## 13. Phase 9: Tier 2 Semantic and Elastic Evidence

### Goal

Add semantic and historical analysis without weakening Tier 1.

### Backend work

Implement a limited Tier 2:

- intent/action semantic similarity,
- argument-scope comparison,
- selected-agent historical precedents,
- labeled approved/blocked retrieval,
- simple sequence statistics,
- explicit confidence and evidence quality.

Elastic queries must filter by workspace and compatible agent/capability.

Tier 2 initially recommends:

- allow,
- warn,
- require approval.

It does not independently bypass or weaken Tier 1. Model-based block remains disabled
unless explicitly added later.

### UI work

Live Interception:

- Tier 2 status and latency,
- semantic signals,
- precedent cards,
- evidence quality,
- Elastic degraded status.

Trace Replay:

- retrieved precedent IDs,
- semantic model/version,
- explanation of any escalation.

Operations:

- Tier 2 invocation rate,
- degraded/failure count,
- V2 latency percentiles.

### Automated verification

- Agent/workspace filters prevent cross-agent evidence.
- Elastic outage applies policy fallback.
- No precedent is treated as insufficient evidence.
- Similar blocked precedent can escalate an otherwise permitted side effect to approval.
- Tier 1 block remains block.

### Manual UI tests

Run a normal scenario and one intentional mismatch:

```text
List files in the workspace.
```

Then induce or directly test a proposal that writes or sends beyond the request.

Expected:

- Tier 2 evidence is visible,
- absence of evidence is explicit,
- Tier 1 remains authoritative.

### Exit gate

Tier 2 must demonstrate measurable scenario value over Tier 1 alone.

## 14. Phase 10: Tier 3 Structured LLM Judge

Status as of 2026-06-08: partially implemented. The backend Tier 3 judge, shared
tier-result contract, Gemini provider, timeout/failure fallback, and deterministic
combiner are implemented. UI presentation, durable TierResult storage, broader
sanitization/redaction, and calibrated routing remain.

### Goal

Use an LLM only for configured ambiguous, consequential actions.

### Backend work

Implement:

- sanitized judge packet, partly implemented with bounded trace/action/policy context,
- trusted prompt template, implemented,
- structured response schema, implemented,
- timeout, implemented,
- confidence threshold, implemented,
- malformed-output handling, implemented as fail-closed Tier 3 failure,
- model and prompt version recording, implemented.

Initial routes:

- ambiguous Gmail send,
- selected ambiguous shell actions not already blocked.

Tier 3 cannot weaken Tier 1.

Current runtime flags:

```text
AGENTGUARD_TIER_3_ENABLED=false
AGENTGUARD_TIER3_ENFORCEMENT_ENABLED=false
AGENTGUARD_TIER3_MODEL=gemini-2.5-flash
AGENTGUARD_MOCK_PIPELINE_ONLY=false
```

### UI work

Live Interception:

- whether Tier 3 ran,
- model and prompt version,
- structured verdict,
- confidence,
- applicable rule IDs,
- uncertainty,
- fallback reason on failure.

Trace Replay:

- persisted judge result,
- sanitized context summary.

### Automated verification

- Tier 1 block bypasses Tier 3.
- Judge cannot return an unknown rule ID as authoritative.
- Malformed output applies fallback.
- Timeout applies fallback.
- Low confidence requires approval for side effects.
- Sensitive values are absent from judge input logs.

### Manual UI tests

Use:

```text
Take care of the latest finance email, but let me check anything consequential.
```

Expected:

- intent is marked ambiguous,
- Tier 2 and Tier 3 run,
- send or other consequential action requires approval,
- judge evidence is visible.

### Exit gate

Tier 3 adds understandable evidence without becoming the policy authority. Backend
tests now cover shadow evidence, enforcement escalation, deterministic-block precedence,
and mock-pipeline non-execution.

## 15. Phase 11: Decision V2 and Complete Replay

### Goal

Make the final V2 decision record the single source of truth.

### Backend work

Finalize `GuardDecisionV2`:

- policy ID, version, and hash,
- argument hash,
- normalized action ID,
- intent ID,
- tiers planned and run,
- matched rules,
- tier result IDs,
- final precedence,
- runtime action,
- complete latency.

Update dashboard repositories and exports.

### UI work

Live Interception:

- final decision flow visualization.

Trace Replay:

- complete V2 timeline.

Decision Memory:

- filter by policy version, capability, tier, and rule ID.

Operations:

- policy, tier, capability, and failure metrics.

### Automated verification

- Every V2 decision can be reproduced from persisted referenced records.
- Export includes policy and tier evidence.
- V1 traces remain readable with a legacy marker.

### Manual UI test

Select one allowed and one blocked session.

Expected:

- both can be explained from intent through execution,
- no evidence panel relies on hidden in-memory state.

### Exit gate

V2 is the dashboard's authoritative decision model.

## 16. Phase 12: Durable Approval

### Goal

Replace the current synthetic approval stop with a secure pending-action workflow.

This phase is optional for the initial hackathon demo.

### Backend work

- Persist pending action.
- Bind it to the exact argument hash and policy version.
- Add expiration.
- Record operator identity and action.
- Issue single-use authorization.
- Redispatch or resume only the exact approved call.

### UI work

Live Interception:

- approve, reject, abort,
- pending expiration,
- exact action summary,
- operator note.

### Verification

- Changed arguments invalidate approval.
- Approval cannot be reused.
- Expired approval cannot execute.
- Reject and abort are terminal and auditable.

## 17. Recommended Checkpoints

The user should manually test and approve these checkpoints:

| Checkpoint | End of phase | What becomes visible |
| --- | --- | --- |
| A | Phase 0 | Reliable real ADK live events |
| B | Phase 2 | Tool capabilities and support status |
| C | Phase 3 | Real policy and policy version |
| D | Phase 4 | Normalized shell/Gmail actions |
| E | Phase 5 | Structured user intent |
| F | Phase 6 | Tier 1 shadow recommendations |
| G | Phase 7 | Tier 1 active enforcement |
| H | Phase 8 | Guided policy editing |
| I | Phase 9 | Tier 2 Elastic evidence |
| J | Phase 10 | Tier 3 judge evidence |
| K | Phase 11 | Full V2 replay and memory |

We should not start the next behavior-changing checkpoint until the current UI output is
understood and accepted.

## 18. Immediate First Development Cycle

The first implementation cycle should include only:

1. Phase 0 runtime correctness.
2. Phase 1 V2 skeleton and shadow mode.
3. Phase 2 capability registry.

At the end of this cycle, the user can:

- run the real Google ADK agent,
- see reliable events,
- see V1 enforcement,
- see a V2 shadow evaluation,
- inspect standardized capabilities for every enabled tool.

No new policy enforcement will be activated yet. This limits risk while establishing the
foundation required by every later phase.

## 19. Testing Responsibilities

### Automated by development

- unit tests,
- schema tests,
- API tests,
- repository tests,
- ADK callback tests,
- frontend build and component tests,
- safety regression scenarios.

### Manual user verification

At each checkpoint, the user verifies:

- the UI describes the action correctly,
- the intent interpretation is reasonable,
- policy controls match expectations,
- allowed actions actually execute,
- blocked actions do not execute,
- evidence is understandable.

Environment-dependent testing may require the user for:

- Gemini API calls,
- Gmail OAuth/MCP,
- browser interaction,
- external Elastic connectivity.

## 20. Definition of V2 Demo Complete

The V2 hackathon demo is complete after Phase 11 when:

- the Google ADK agent uses FirewallV2,
- every call has a normalized action,
- every turn has a stable intent contract,
- every call passes Tier 1,
- active policy is versioned and user-visible,
- policy changes are possible through guided controls,
- Tier 2 provides scoped semantic and Elastic evidence,
- Tier 3 runs only for configured ambiguous cases,
- explicit policy cannot be overridden,
- blocked calls do not execute,
- all evidence is visible in Live Interception and Trace Replay,
- the safety scenario suite passes.

Durable approval continuation can remain a clearly documented post-hackathon phase.
