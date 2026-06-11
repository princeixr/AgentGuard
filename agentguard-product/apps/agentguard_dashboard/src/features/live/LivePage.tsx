import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  ChevronDown,
  CircleCheck,
  CircleX,
  ShieldAlert,
  X,
} from "lucide-react";
import { memo, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api } from "../../api/client";
import type {
  AgentPolicy,
  PendingApproval,
  PrecedentSummary,
  ReplayStep,
} from "../../api/types";
import { useProductionAgent } from "../../api/useProductionAgent";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";

export function LivePage() {
  const queryClient = useQueryClient();
  const { agent, agentId, agents } = useProductionAgent();
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const current = useQuery({
    queryKey: ["interception", agentId],
    queryFn: () => api.currentInterception(agentId),
    enabled: Boolean(agentId),
    refetchInterval: 2_000,
  });
  const sessions = useQuery({
    queryKey: ["sessions", agentId],
    queryFn: () => api.sessions(agentId),
    enabled: Boolean(agentId),
    refetchInterval: 3_000,
  });
  const approvals = useQuery({
    queryKey: ["approvals"],
    queryFn: () => api.approvals("all"),
    refetchInterval: 2_000,
  });
  const policy = useQuery({
    queryKey: ["agent-policy", agentId],
    queryFn: () => api.agentPolicy(agentId),
    enabled: Boolean(agentId),
  });

  const productionCurrent =
    current.data && current.data.scenario_id === null ? current.data : null;
  const latestSession = useMemo(
    () =>
      sessions.data
        ?.filter((session) => session.scenario_id === null)
        .sort(
          (a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
        )[0],
    [sessions.data],
  );
  const sessionId = productionCurrent?.session_id ?? latestSession?.session_id;
  const session = useQuery({
    queryKey: ["session", agentId, sessionId],
    queryFn: () => api.session(agentId, sessionId!),
    enabled: Boolean(agentId && sessionId),
    refetchInterval: 2_000,
  });
  const agentApprovals =
    approvals.data?.items.filter((item) => item.agent_id === agentId) ?? [];
  const approvalByTrace = new Map(
    agentApprovals.map((item) => [item.trace_id, item]),
  );
  const pending = agentApprovals.filter((item) => item.status === "pending");
  const pendingTraceIds = new Set(pending.map((item) => item.trace_id));
  const pendingStep = session.data?.steps
    .slice()
    .reverse()
    .find((step) => pendingTraceIds.has(step.trace_id));
  const selectedStep =
    session.data?.steps.find((step) => step.trace_id === selectedTraceId) ??
    pendingStep ??
    session.data?.steps.at(-1);
  const selectedDetail = useQuery({
    queryKey: ["memory-detail", agentId, selectedStep?.trace_id],
    queryFn: () => api.memoryDetail(agentId, selectedStep!.trace_id),
    enabled: Boolean(agentId && selectedStep?.trace_id),
  });

  useEffect(() => {
    if (!agentId) return;
    const source = new EventSource(
      `/api/v1/agents/${encodeURIComponent(agentId)}/events/stream`,
    );
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: ["interception", agentId] });
      void queryClient.invalidateQueries({ queryKey: ["sessions", agentId] });
      void queryClient.invalidateQueries({ queryKey: ["session", agentId] });
      void queryClient.invalidateQueries({ queryKey: ["operations", agentId] });
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
    };
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.onmessage = refresh;
    source.addEventListener("state", refresh);
    source.addEventListener("live_event", refresh);
    return () => source.close();
  }, [agentId, queryClient]);

  if (agents.isLoading) return <LoadingState label="Loading live runtime" />;
  if (agents.error) return <ErrorState message="Unable to load connected agents." />;
  if (!agent) {
    return (
      <div className="card">
        <EmptyState
          title="No connected agent"
          message="Register an agent through the SDK to start interception."
        />
      </div>
    );
  }

  return (
    <div className="page">
      <section className="card live-status">
        <div className="agent-identity">
          <div className="live-dot" />
          <div>
            <div className="agent-name">{agent.name}</div>
            <div className="mono" style={{ color: "var(--text-secondary)", fontSize: 11 }}>
              session_id: {sessionId ?? "waiting_for_runtime"}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>
            {connected ? "SSE connected" : "Polling fallback"}
          </span>
          <StatusChip value={productionCurrent?.status ?? "idle"} />
        </div>
      </section>

      {session.isLoading ? (
        <div className="card"><LoadingState label="Loading live traces" /></div>
      ) : session.data?.steps.length ? (
        <section className="live-workspace-grid">
          {policy.data && (
            <>
              <SessionQueryContext
                key={session.data.session.session_id}
                policy={policy.data}
                sessionId={session.data.session.session_id}
                sourceStep={session.data.steps[0]}
                userQuery={session.data.session.user_intent}
              />
            </>
          )}

          <section className="live-feed-section">
            <div className="row-between live-feed-heading">
              <h2>Live Trace Feed</h2>
              <span className="mono">
                {session.data.steps.length} recorded calls
              </span>
            </div>

            {pending.length > 0 && (
              <ApprovalBanner
                approval={pending[0]}
                pendingCount={pending.length}
                onFocus={() => setSelectedTraceId(pending[0].trace_id)}
              />
            )}

            <div className="feed timeline-feed">
              {session.data.steps
                .slice()
                .reverse()
                .map((step, index) => {
                  const approval = approvalByTrace.get(step.trace_id);
                  const tone = decisionTone(step, approval);
                  return (
                    <div
                      className={[
                        "timeline-entry",
                        `timeline-entry-${tone}`,
                        index === 0 ? "timeline-entry-newest" : "",
                      ].filter(Boolean).join(" ")}
                      key={step.trace_id}
                    >
                      <span className="timeline-dot" aria-hidden="true" />
                      <button
                        aria-pressed={selectedStep?.trace_id === step.trace_id}
                        className={[
                          "feed-row",
                          `feed-row-${tone}`,
                          pendingTraceIds.has(step.trace_id) ? "feed-row-paused" : "",
                          selectedStep?.trace_id === step.trace_id ? "feed-row-selected" : "",
                        ].filter(Boolean).join(" ")}
                        onClick={() => setSelectedTraceId(step.trace_id)}
                        type="button"
                      >
                        <div className="feed-tool">
                          <code>{step.tool_name}</code>
                          {pendingTraceIds.has(step.trace_id) && (
                            <span className="feed-pause-label">
                              <ShieldAlert size={11} />
                              Execution paused here
                            </span>
                          )}
                        </div>
                        <span className="feed-argument">
                          {step.argument_summary}
                        </span>
                        <span className="mono feed-evaluator">
                          {step.guard_evaluation?.combined_decision?.enforced_by?.toString() ??
                            step.guard_evaluation?.enforced_by ??
                            "firewall_v2"}
                        </span>
                        <StatusChip value={displayVerdict(step, approval)} />
                      </button>
                    </div>
                  );
                })}
            </div>
          </section>

          {selectedStep && (
            <div className="live-detail-column">
              <InterceptionDetail
                approval={approvalByTrace.get(selectedStep.trace_id)}
                evidenceLoading={selectedDetail.isLoading}
                intentContractDisclosure={policy.data ? (
                  <IntentContractContext
                    key={`contract-${session.data.session.session_id}`}
                    policy={policy.data}
                    sessionId={session.data.session.session_id}
                    sourceStep={session.data.steps[0]}
                    userQuery={session.data.session.user_intent}
                  />
                ) : undefined}
                precedents={selectedDetail.data?.precedents ?? []}
                step={selectedStep}
                userIntent={session.data.session.user_intent}
              />
            </div>
          )}
        </section>
      ) : (
        <div className="card">
          <EmptyState
            title="Waiting for production traffic"
            message="Tool proposals submitted through the AgentGuard SDK will stream here."
          />
        </div>
      )}
    </div>
  );
}

interface SessionContextProps {
  policy: AgentPolicy;
  sessionId: string;
  sourceStep: ReplayStep;
  userQuery: string;
}

export const SessionQueryContext = memo(function SessionQueryContext({
  policy,
  sourceStep,
  userQuery,
}: SessionContextProps) {
  const contract = asRecord(sourceStep.guard_evaluation?.intent_contract);
  const snapshot = useMemo(
    () => buildSessionContext(contract, policy, userQuery),
    [],
  );

  return (
    <section className="session-context session-query-context" aria-label="Session Context">
      <div className="section-heading">
        <div>
          <div className="eyebrow">Session Context</div>
          <h2>Query and authorization boundary</h2>
        </div>
        <span className={`scope-confidence scope-confidence-${snapshot.scopeTone}`}>
          {snapshot.scopeLabel}
          {snapshot.confidence !== null && (
            <small>{Math.round(snapshot.confidence * 100)}%</small>
          )}
        </span>
      </div>

      <article className="card session-query-card">
        <div className="eyebrow">User Query</div>
        <blockquote>“{snapshot.userQuery}”</blockquote>
      </article>
    </section>
  );
}, (previous, next) => previous.sessionId === next.sessionId);

export const IntentContractContext = memo(function IntentContractContext({
  policy,
  sourceStep,
  userQuery,
}: SessionContextProps) {
  const contract = asRecord(sourceStep.guard_evaluation?.intent_contract);
  const snapshot = useMemo(
    () => buildSessionContext(contract, policy, userQuery),
    [],
  );

  return (
    <details
      aria-label="Intent Contract"
      className="detail-disclosure intent-contract-card"
    >
      <summary>
        <span>
          <span className="eyebrow">Intent Contract</span>
          <small>Effective capabilities and operations for this session.</small>
        </span>
        <span className="intent-contract-summary-meta">
          <code>{snapshot.extractor}</code>
          <ChevronDown size={16} />
        </span>
      </summary>
      <div className="contract-rows">
        <ContractColumn
          emptyLabel="No explicit allowed capabilities"
          items={snapshot.allowed}
          label="Allowed"
          tone="allowed"
        />
        <ContractColumn
          emptyLabel="No approval-gated capabilities"
          items={snapshot.requiresApproval}
          label="Requires Approval"
          tone="approval"
        />
        <ContractColumn
          emptyLabel="No explicit forbidden capabilities"
          items={snapshot.forbidden}
          label="Forbidden"
          tone="forbidden"
        />
      </div>
    </details>
  );
}, (previous, next) => previous.sessionId === next.sessionId);

function ContractColumn({
  emptyLabel,
  items,
  label,
  tone,
}: {
  emptyLabel: string;
  items: string[];
  label: string;
  tone: "allowed" | "approval" | "forbidden";
}) {
  return (
    <div className={`contract-column contract-column-${tone}`}>
      <div className="contract-column-title">
        <span>{label}</span>
        <small>{items.length}</small>
      </div>
      {items.length ? (
        <ul>
          {items.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : (
        <p>{emptyLabel}</p>
      )}
    </div>
  );
}

function ApprovalBanner({
  approval,
  pendingCount,
  onFocus,
}: {
  approval: PendingApproval;
  pendingCount: number;
  onFocus: () => void;
}) {
  const queryClient = useQueryClient();
  const resolve = useMutation({
    mutationFn: (action: "approve" | "reject") =>
      action === "approve"
        ? api.approve(approval.approval_id)
        : api.reject(approval.approval_id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["approvals"] }),
        queryClient.invalidateQueries({ queryKey: ["interception", approval.agent_id] }),
        queryClient.invalidateQueries({ queryKey: ["sessions", approval.agent_id] }),
        queryClient.invalidateQueries({ queryKey: ["session", approval.agent_id] }),
      ]);
    },
  });

  return (
    <article className="approval-banner">
      <button className="approval-banner-focus" onClick={onFocus} type="button">
        <span className="approval-banner-icon"><ShieldAlert size={18} /></span>
        <span>
          <strong>Execution paused — operator decision required</strong>
          <small>
            {approval.tool_name}
            {pendingCount > 1 ? ` · ${pendingCount} pending actions` : ""}
          </small>
        </span>
      </button>
      <div className="approval-banner-actions">
        <button
          className="button button-danger"
          disabled={resolve.isPending}
          onClick={() => resolve.mutate("reject")}
          type="button"
        >
          <X size={14} /> Deny
        </button>
        <button
          className="button button-warning"
          disabled={resolve.isPending}
          onClick={() => resolve.mutate("approve")}
          type="button"
        >
          <Check size={14} /> Approve
        </button>
      </div>
    </article>
  );
}

export function InterceptionDetail({
  approval,
  evidenceLoading,
  intentContractDisclosure,
  precedents,
  step,
  userIntent,
}: {
  approval?: PendingApproval;
  evidenceLoading: boolean;
  intentContractDisclosure?: ReactNode;
  precedents: PrecedentSummary[];
  step: ReplayStep;
  userIntent: string;
}) {
  const evaluation = step.guard_evaluation;
  const verdict = displayVerdict(step, approval);
  const tone = decisionTone(step, approval);
  const intentContract = asRecord(evaluation?.intent_contract);
  const authorization = asRecord(evaluation?.intent_authorization);
  const normalizedAction = asRecord(evaluation?.normalized_action);
  const attemptedTone = intentGapTone(authorization);
  const requestedText =
    stringValue(intentContract?.raw_user_request) ||
    approval?.user_request ||
    userIntent;
  const enforcedBy =
    stringValue(asRecord(evaluation?.combined_decision)?.enforced_by) ||
    evaluation?.enforced_by ||
    "firewall_v2";
  const evaluator = enforcedBy;
  const fallbackUsed = enforcedBy.includes("fallback");
  const tierTwo = evaluation?.tier_results.find(
    (tier) => stringValue(tier.tier) === "tier_2",
  );

  return (
    <aside className="card detail-panel">
      <section className={`verdict-hero verdict-hero-${tone}`}>
        <div className="verdict-icon" aria-hidden="true">
          {tone === "block" ? (
            <CircleX size={30} />
          ) : tone === "approval" ? (
            <ShieldAlert size={30} />
          ) : (
            <CircleCheck size={30} />
          )}
        </div>
        <div>
          <div className="eyebrow">Enforcement verdict</div>
          <h2>{verdict.replaceAll("_", " ")}</h2>
          <div className="mono verdict-evaluator">{evaluator}</div>
        </div>
      </section>

      <section className="intent-action-section">
        <div className="intent-action-card intent-requested">
          <div className="intent-action-heading">
            <span className="eyebrow">User requested</span>
          </div>
          <blockquote>“{requestedText || "User request unavailable."}”</blockquote>
          <ScopeList contract={intentContract} />
        </div>
        <div className={`intent-action-card intent-attempted intent-attempted-${attemptedTone}`}>
          <div className="intent-action-heading">
            <span className="eyebrow">Agent attempted</span>
          </div>
          <div className="attempted-action">
            <code>{step.tool_name}</code>
            <strong>{actionSummary(normalizedAction, step)}</strong>
          </div>
          <div className="mono attempted-payload">{step.argument_summary}</div>
          <GapSignals authorization={authorization} />
        </div>
      </section>

      <section className="decision-basis">
        <div className="eyebrow">Decision basis</div>
        <p>
          {evaluation?.explanation ?? step.explanation}
          {fallbackUsed && (
            <span className="fallback-disclosure">
              No explicit enforcing rule produced this verdict; AgentGuard used the
              conservative <code>{enforcedBy}</code> path.
            </span>
          )}
        </p>
      </section>

      <details className="detail-disclosure">
        <summary>
          <span>
            <span className="eyebrow">Evidence / precedent</span>
            <small>{precedents.length} related historical actions</small>
          </span>
          <ChevronDown size={16} />
        </summary>
        <div className="disclosure-content">
          {tierTwo && (
            <div className="tier-two-status">
              <div className="row-between">
                <code>tier_2 semantic evidence</code>
                <StatusChip value={stringValue(tierTwo.status) || "not_available"} />
              </div>
              <p>{stringValue(tierTwo.explanation)}</p>
            </div>
          )}
          {evidenceLoading ? (
            <div className="evidence-empty">Loading historical evidence…</div>
          ) : precedents.length ? (
            <div className="precedent-list">
              {precedents.map((precedent) => (
                <article className="precedent-row" key={precedent.trace_id}>
                  <div>
                    <code>{precedent.tool_name}</code>
                    <p>{precedent.intent}</p>
                  </div>
                  <div className="precedent-score">
                    <span className="mono">
                      {Math.round(precedent.risk_score * 100)} score
                    </span>
                    <StatusChip value={precedent.decision} />
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="evidence-empty">
              No related historical actions were found for this trace.
            </div>
          )}
        </div>
      </details>

      <TechnicalDisclosure
        label="Raw call payload"
        payload={step.arguments}
      />
      {intentContractDisclosure}
    </aside>
  );
}

function TechnicalDisclosure({
  label,
  payload,
}: {
  label: string;
  payload: unknown;
}) {
  return (
    <details className="detail-disclosure technical-disclosure">
      <summary>
        <span className="eyebrow">{label}</span>
        <ChevronDown size={16} />
      </summary>
      <div className="disclosure-content">
        <pre className="json">{JSON.stringify(payload, null, 2)}</pre>
      </div>
    </details>
  );
}

function ScopeList({ contract }: { contract: Record<string, unknown> | null }) {
  const capabilities = stringArray(contract?.requested_capabilities);
  const resources = stringArray(contract?.permitted_resources);
  if (!capabilities.length && !resources.length) return null;
  return (
    <div className="scope-list">
      {capabilities.map((capability) => (
        <span className="tag" key={capability}>{capability}</span>
      ))}
      {resources.map((resource) => (
        <span className="tag mono" key={resource}>{resource}</span>
      ))}
    </div>
  );
}

function GapSignals({
  authorization,
}: {
  authorization: Record<string, unknown> | null;
}) {
  const signals = [
    ...stringArray(authorization?.unauthorized_capabilities),
    ...stringArray(authorization?.matched_forbidden_capabilities),
    ...stringArray(authorization?.forbidden_resources),
    ...stringArray(authorization?.destination_violations),
  ];
  if (!signals.length) return null;
  return (
    <div className="gap-signals">
      {signals.map((signal) => <span key={signal}>{signal}</span>)}
    </div>
  );
}

function displayVerdict(step: ReplayStep, approval?: PendingApproval) {
  if (approval?.status === "approved") return "approved";
  if (approval?.status === "rejected") return "rejected";
  return step.guard_evaluation?.recommendation ?? step.decision;
}

function decisionTone(step: ReplayStep, approval?: PendingApproval) {
  const decision = displayVerdict(step, approval);
  if (decision === "approved") return "approved";
  if (decision === "block" || decision === "rejected") return "block";
  if (decision === "require_approval" || decision === "review") return "approval";
  return "allow";
}

function intentGapTone(authorization: Record<string, unknown> | null) {
  const recommendation = stringValue(authorization?.recommendation);
  const hasHardViolation = [
    "unauthorized_capabilities",
    "matched_forbidden_capabilities",
    "forbidden_resources",
    "destination_violations",
  ].some((field) => stringArray(authorization?.[field]).length > 0);
  if (hasHardViolation || recommendation === "block") return "block";
  if (recommendation === "require_approval") return "approval";
  return "allow";
}

function actionSummary(
  normalizedAction: Record<string, unknown> | null,
  step: ReplayStep,
) {
  const operation = stringValue(normalizedAction?.operation) || step.tool_category;
  const resources = Array.isArray(normalizedAction?.resources)
    ? normalizedAction.resources
        .map((item) => stringValue(asRecord(item)?.value))
        .filter(Boolean)
    : [];
  return resources.length ? `${operation} · ${resources.join(", ")}` : operation;
}

function buildSessionContext(
  contract: Record<string, unknown> | null,
  policy: AgentPolicy,
  fallbackQuery: string,
) {
  const extractor = asRecord(contract?.extractor);
  const confidenceValue = extractor?.confidence;
  const confidence =
    typeof confidenceValue === "number" ? confidenceValue : null;
  const uncertainties = stringArray(contract?.uncertainties);
  const allowed = unique([
    ...stringArray(contract?.requested_capabilities),
    ...stringArray(contract?.permitted_resources).map(
      (resource) => `resource: ${resource}`,
    ),
  ]);
  const requiresApproval = unique([
    ...policyItems(policy, "require_approval"),
    ...uncertainties.map((uncertainty) => `uncertain: ${uncertainty}`),
    ...(contract?.side_effect_authorized === false
      ? ["unrequested side effects"]
      : []),
  ]);
  const forbidden = unique([
    ...stringArray(contract?.forbidden_capabilities),
    ...stringArray(contract?.forbidden_resources).map(
      (resource) => `resource: ${resource}`,
    ),
    ...policyItems(policy, "block"),
  ]);
  const scopeDefined =
    confidence !== null &&
    confidence >= 0.7 &&
    uncertainties.length === 0;

  return {
    allowed,
    confidence,
    extractor:
      stringValue(extractor?.name) ||
      stringValue(extractor?.method) ||
      "intent_contract_v2",
    forbidden,
    requiresApproval,
    scopeLabel: scopeDefined ? "SCOPE_DEFINED" : "SCOPE_UNCERTAIN",
    scopeTone: scopeDefined ? "defined" : "uncertain",
    userQuery:
      stringValue(contract?.raw_user_request) ||
      fallbackQuery ||
      "User request unavailable.",
  };
}

function policyItems(
  policy: AgentPolicy,
  effect: "require_approval" | "block",
) {
  return policy.document.rules
    .filter((rule) => rule.effect === effect)
    .flatMap((rule) => [
      ...rule.match.capabilities_any,
      ...rule.match.tools_any.map((tool) => `tool: ${tool}`),
      ...Object.keys(rule.match.resource_constraints).map(
        (constraint) => `constraint: ${constraint.replaceAll("_", " ")}`,
      ),
    ]);
}

function unique(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}
