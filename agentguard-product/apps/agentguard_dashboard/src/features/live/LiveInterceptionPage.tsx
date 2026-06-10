import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  Search,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import { useLiveEvents } from "../../api/useLiveEvents";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function LiveInterceptionPage() {
  const { agentId = "" } = useParams();
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const connected = useLiveEvents(agentId);
  const interception = useQuery({
    queryKey: ["interception", agentId],
    queryFn: () => api.currentInterception(agentId),
    refetchInterval: connected ? false : 1_000,
  });
  const sessionId = interception.data?.session_id;
  const session = useQuery({
    queryKey: ["session", agentId, sessionId],
    queryFn: () => api.session(agentId, sessionId!),
    enabled: Boolean(sessionId),
  });
  const selectedDetail = useQuery({
    queryKey: ["memory-detail", agentId, selectedTraceId],
    queryFn: () => api.memoryDetail(agentId, selectedTraceId!),
    enabled: Boolean(selectedTraceId),
  });
  useEffect(() => {
    setSelectedTraceId(null);
  }, [sessionId]);
  if (interception.isLoading) {
    return <LoadingState label="Loading interception console" />;
  }
  if (interception.error) {
    return <ErrorState message="The interception API is unavailable." />;
  }

  const state = interception.data!;
  const detail = selectedDetail.data ?? state.detail;
  const guardEvaluation = detail?.item.guard_evaluation;
  const normalizedAction = guardEvaluation?.normalized_action;
  const intentContract = guardEvaluation?.intent_contract;
  const intentAuthorization = guardEvaluation?.intent_authorization;
  const displayedDecision =
    guardEvaluation?.recommendation ?? detail?.item.decision;
  const observeOnly = guardEvaluation?.enforcement_status === "observe_only";
  const decisionOwner = guardEvaluation
    ? observeOnly
      ? "AgentGuard FirewallV2 recommendation"
      : "AgentGuard FirewallV2 enforced decision"
    : "Historical trace without V2 evidence";
  const displayedExplanation =
    guardEvaluation?.explanation || detail?.item.explanation;
  const visibleSteps =
    session.data?.steps.filter((step) => step.step_index <= state.current_step) ?? [];
  const idle = state.status === "idle";

  return (
    <div className="flex h-full min-h-[720px] flex-col gap-4">
      <section className="panel flex items-center justify-between px-5 py-3">
        <div className="flex items-center gap-8">
          <div>
            <div className="eyebrow">Intent</div>
            <div className="mt-1 max-w-[520px] text-sm font-medium">
              {detail?.trace.intent.normalized_intent ??
                "Run the selected registered agent to inspect its tool calls."}
            </div>
          </div>
          <div>
            <div className="eyebrow">Progress</div>
            <div className="mt-1 mono text-sm">
              Step {state.current_step}/{state.total_steps}
            </div>
          </div>
          <div>
            <div className="eyebrow">Stream</div>
            <div className="mt-1 flex items-center gap-2 text-sm">
              <span
                className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-amber-500"}`}
              />
              {connected ? "Runtime events connected" : "Polling fallback"}
            </div>
          </div>
          <div>
            <div className="eyebrow">Firewall</div>
            <div className="mt-1 mono text-sm">
              {state.firewall_mode} · {state.guard_version}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge value={state.status} />
          <Link
            className="rounded bg-black px-4 py-2 text-xs font-semibold text-white"
            to={`/agents/${agentId}`}
          >
            View Agent
          </Link>
        </div>
      </section>

      <div className="page-grid flex-1 grid-cols-[minmax(300px,0.9fr)_minmax(420px,1.15fr)_minmax(280px,0.9fr)]">
        <section className="panel min-h-0 overflow-hidden">
          <div className="flex h-13 items-center justify-between border-b border-[var(--border)] px-5">
            <h2 className="eyebrow text-[var(--ink)]">Agent Stream</h2>
            <StatusBadge value={state.status} />
          </div>
          <div className="h-[calc(100%-52px)] overflow-auto p-5 subtle-scrollbar">
            {idle ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--surface-container)]">
                  <ShieldAlert size={20} />
                </div>
                <div className="font-semibold">No active interception</div>
                <p className="mt-2 max-w-[260px] text-sm text-[var(--ink-muted)]">
                  Run the independent agent from its own UI. Tool proposals and
                  AgentGuard decisions will stream here after transport is connected.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded border border-[var(--border)] bg-[var(--surface-low)] p-4">
                  <div className="eyebrow">User input</div>
                  <p className="mt-2 text-sm leading-5">
                    {detail?.trace.intent.raw_user_request}
                  </p>
                </div>
                {visibleSteps.map((step) => {
                  const stepDecision =
                    step.guard_evaluation?.recommendation ?? step.decision;
                  const selected =
                    step.trace_id ===
                    (selectedTraceId ?? state.current_trace_id);
                  return (
                  <button
                    aria-pressed={selected}
                    className={`relative rounded border p-4 ${
                      selected
                        ? "border-amber-400 bg-amber-50/60"
                        : "border-[var(--border)]"
                    } block w-full text-left`}
                    key={step.trace_id}
                    onClick={() => setSelectedTraceId(step.trace_id)}
                    type="button"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <code className="text-xs font-semibold">
                          {step.tool_name}
                        </code>
                        <div className="mt-1 text-[9px] font-bold uppercase tracking-wider text-[var(--ink-muted)]">
                          {step.guard_evaluation
                            ? `${step.guard_evaluation.firewall_mode} · ${step.guard_evaluation.enforced_by}`
                            : "Historical trace"}
                        </div>
                      </div>
                      <StatusBadge value={stepDecision} />
                    </div>
                    <div className="mt-2 truncate mono text-[11px] text-[var(--ink-muted)]">
                      {step.argument_summary}
                    </div>
                    {step.guard_evaluation?.enforcement_status ===
                      "observe_only" && (
                      <div className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-blue-700">
                        Observe only · tool execution used the legacy decision
                      </div>
                    )}
                  </button>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        <section className="panel min-h-0 overflow-hidden">
          {detail ? (
            <div className="flex h-full flex-col">
              <div
                className={`border-b px-5 py-5 ${
                  state.status === "paused"
                    ? "border-amber-300 bg-[var(--amber-bg)]"
                    : "border-[var(--border)]"
                }`}
              >
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--amber)]">
                  {state.status === "paused" ? (
                    <ShieldAlert size={17} />
                  ) : (
                    <Check size={17} />
                  )}
                  {state.status === "paused"
                    ? "Execution paused · operator decision required"
                    : decisionOwner}
                </div>
                <div className="mt-3 flex items-end justify-between gap-4">
                  <code className="text-2xl font-bold">
                    {detail.item.tool_name}
                  </code>
                  <StatusBadge value={displayedDecision ?? "unknown"} />
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-auto p-5 subtle-scrollbar">
                <div className="grid grid-cols-[130px_1fr] gap-5">
                  <div className="flex h-28 w-28 flex-col items-center justify-center rounded-full border-[9px] border-amber-500 bg-white">
                    <div className="text-center text-sm font-bold uppercase">
                      {String(displayedDecision).replaceAll("_", " ")}
                    </div>
                    <div className="eyebrow mt-1">V2 result</div>
                  </div>
                  <div>
                    <div className="eyebrow">{decisionOwner}</div>
                    <p className="mt-2 text-sm leading-6">
                      {displayedExplanation}
                    </p>
                    {observeOnly && (
                      <p className="mt-2 rounded bg-blue-50 px-3 py-2 text-xs font-medium text-blue-800">
                        This result was recorded in shadow mode and did not
                        control tool execution.
                      </p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-2">
                      {detail.item.labels.map((label) => (
                        <span
                          className="rounded border border-[var(--border)] bg-[var(--surface-low)] px-2 py-1 mono text-[10px]"
                          key={label}
                        >
                          {label.replaceAll("_", " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-6 grid grid-cols-2 gap-3">
                  <div className="rounded border border-[var(--border)] p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="eyebrow">Authorized intent</div>
                      {intentAuthorization?.recommendation && (
                        <StatusBadge
                          value={String(intentAuthorization.recommendation)}
                        />
                      )}
                    </div>
                    {intentContract ? (
                      <div className="mt-3 space-y-3">
                        <code className="block text-[10px] text-[var(--ink-muted)]">
                          {String(intentContract.intent_id)}
                        </code>
                        <IntentValues
                          label="Requested"
                          values={intentContract.requested_capabilities}
                        />
                        <IntentValues
                          label="Forbidden"
                          values={intentContract.forbidden_capabilities}
                          warning
                        />
                        <IntentValues
                          label="Resources"
                          values={intentContract.permitted_resources}
                        />
                        <IntentValues
                          label="Destinations"
                          values={intentContract.destinations}
                        />
                        <div className="text-[10px] text-[var(--ink-muted)]">
                          Extractor:{" "}
                          {String(
                            (intentContract.extractor as Record<string, unknown>)
                              ?.name ?? "unknown",
                          )}{" "}
                          · confidence{" "}
                          {Math.round(
                            Number(
                              (intentContract.extractor as Record<string, unknown>)
                                ?.confidence ?? 0,
                            ) * 100,
                          )}
                          %
                        </div>
                      </div>
                    ) : (
                      <p className="mt-2 text-sm leading-5">
                        {detail.trace.intent.normalized_intent}
                      </p>
                    )}
                  </div>
                  <div className="rounded border border-amber-300 bg-amber-50 p-4">
                    <div className="eyebrow text-[var(--amber)]">
                      Attempted action
                    </div>
                    <pre className="mt-2 overflow-auto whitespace-pre-wrap mono text-[11px] leading-5">
                      {JSON.stringify(
                        detail.trace.proposed_tool_call.arguments,
                        null,
                        2,
                      )}
                    </pre>
                  </div>
                </div>

                <div className="mt-6 rounded border border-[var(--border)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="eyebrow">Decision basis</div>
                    <code className="text-[11px] font-semibold">
                      {guardEvaluation
                        ? `${guardEvaluation.firewall_version} · ${guardEvaluation.enforced_by}`
                        : String(detail.decision.tier_used ?? "decision_policy")}
                    </code>
                  </div>
                  {guardEvaluation?.matched_rules.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {guardEvaluation.matched_rules.map(
                        (rule: { rule_id: string; effect: string }) => (
                          <code
                            className="rounded bg-[var(--red-bg)] px-2 py-1 text-[11px] font-semibold text-[var(--red)]"
                            key={rule.rule_id}
                          >
                            {rule.rule_id}: {rule.effect}
                          </code>
                        ),
                      )}
                    </div>
                  ) : Array.isArray(detail.decision.decision_rules_fired) &&
                    detail.decision.decision_rules_fired.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {detail.decision.decision_rules_fired.map((rule: string) => (
                        <code
                          className="rounded bg-[var(--red-bg)] px-2 py-1 text-[11px] font-semibold text-[var(--red)]"
                          key={rule}
                        >
                          {rule}
                        </code>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-xs text-[var(--ink-muted)]">
                      No explicit policy rule matched. The configured fallback
                      decision was used.
                    </p>
                  )}
                </div>

                <div className="mt-6 rounded border border-blue-200 bg-blue-50/60 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="eyebrow text-blue-700">
                      FirewallV2 evaluation
                    </div>
                    <StatusBadge
                      value={
                        guardEvaluation
                          ? guardEvaluation.enforcement_status.replace("_", " ")
                          : "not run"
                      }
                    />
                  </div>
                  {guardEvaluation ? (
                    <>
                      <p className="mt-2 text-sm leading-5">
                        {guardEvaluation.explanation}
                      </p>
                      {normalizedAction && (
                        <div className="mt-3 rounded border border-blue-200 bg-white p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="eyebrow">Normalized action</div>
                              <div className="mt-1 font-mono text-sm font-semibold">
                                {normalizedAction.operation}
                              </div>
                            </div>
                            <StatusBadge value={normalizedAction.parser.status} />
                          </div>
                          <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-[var(--ink-muted)]">
                            <span>Impact: {normalizedAction.impact}</span>
                            <span>
                              Side effect:{" "}
                              {normalizedAction.side_effect ? "yes" : "no"}
                            </span>
                            <span>
                              Confidence:{" "}
                              {Math.round(
                                normalizedAction.parser.confidence * 100,
                              )}
                              %
                            </span>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {normalizedAction.capabilities.map(
                              (capability: string) => (
                                <code
                                  className="rounded bg-blue-50 px-2 py-1 text-[10px] font-semibold text-blue-800"
                                  key={capability}
                                >
                                  {capability}
                                </code>
                              ),
                            )}
                            {normalizedAction.flags.map((flag: string) => (
                              <code
                                className="rounded bg-[var(--surface-low)] px-2 py-1 text-[10px]"
                                key={flag}
                              >
                                {flag}
                              </code>
                            ))}
                          </div>
                          {normalizedAction.resources.length > 0 && (
                            <div className="mt-3 space-y-1">
                              <div className="eyebrow">Resources</div>
                              {normalizedAction.resources.map(
                                (resource: {
                                  value: string;
                                  access: string;
                                  sensitivity: string;
                                }) => (
                                  <div
                                    className="flex items-center justify-between rounded bg-[var(--surface-low)] px-2 py-1 text-[11px]"
                                    key={`${resource.access}:${resource.value}`}
                                  >
                                    <code>{resource.value}</code>
                                    <span>{resource.access} · {resource.sensitivity}</span>
                                  </div>
                                ),
                              )}
                            </div>
                          )}
                          {normalizedAction.destinations.length > 0 && (
                            <div className="mt-3 space-y-1">
                              <div className="eyebrow">Destinations</div>
                              {normalizedAction.destinations.map(
                                (destination: { value: string; type: string }) => (
                                  <div
                                    className="rounded bg-[var(--surface-low)] px-2 py-1 text-[11px]"
                                    key={`${destination.type}:${destination.value}`}
                                  >
                                    <code>{destination.value}</code>
                                  </div>
                                ),
                              )}
                            </div>
                          )}
                          <p className="mt-3 text-[11px] leading-4 text-[var(--ink-muted)]">
                            {normalizedAction.parser.detail}
                          </p>
                        </div>
                      )}
                      <div className="mt-3 rounded border border-blue-200 bg-white p-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="eyebrow">Policy decision</div>
                            <code className="mt-1 block text-xs">
                              {guardEvaluation.policy_id ?? "unknown"}@
                              {guardEvaluation.policy_version ?? "unknown"}
                            </code>
                          </div>
                          <StatusBadge value={guardEvaluation.recommendation} />
                        </div>
                        {guardEvaluation.matched_rules.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {guardEvaluation.matched_rules.map((rule) => (
                              <code
                                className="rounded bg-blue-50 px-2 py-1 text-[10px] font-semibold text-blue-800"
                                key={rule.rule_id}
                              >
                                {rule.rule_id}: {rule.effect}
                              </code>
                            ))}
                          </div>
                        )}
                        {guardEvaluation.deferred_rule_ids.length > 0 && (
                          <div className="mt-3 text-[11px] text-[var(--ink-muted)]">
                            Deferred rules:{" "}
                            {guardEvaluation.deferred_rule_ids.join(", ")}
                          </div>
                        )}
                      </div>
                      {guardEvaluation.evaluation_plan && (
                        <div className="mt-3 rounded border border-blue-200 bg-white p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="eyebrow">Evaluation route</div>
                              <code className="mt-1 block text-xs font-semibold">
                                {String(guardEvaluation.evaluation_plan.route_class)}
                              </code>
                            </div>
                            <StatusBadge value="operational" />
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {(
                              guardEvaluation.evaluation_plan.required_tiers as string[]
                            ).map((tier) => (
                              <code
                                className="rounded bg-blue-50 px-2 py-1 text-[10px] font-semibold text-blue-800"
                                key={tier}
                              >
                                {tier}
                              </code>
                            ))}
                          </div>
                          <p className="mt-3 text-[11px] text-[var(--ink-muted)]">
                            {(
                              guardEvaluation.evaluation_plan.reasons as string[]
                            ).join("; ")}
                          </p>
                        </div>
                      )}
                      {guardEvaluation.tier_results.length > 0 && (
                        <div className="mt-3 grid gap-2">
                          {guardEvaluation.tier_results.map((tier) => (
                            <div
                              className="rounded border border-blue-200 bg-white p-3 text-xs"
                              key={String(tier.tier_result_id ?? tier.tier)}
                            >
                              <div className="flex items-center justify-between gap-3">
                                <code className="font-semibold">
                                  {String(tier.tier)}
                                </code>
                                <StatusBadge value={String(tier.recommendation)} />
                              </div>
                              <p className="mt-2 text-[var(--ink-muted)]">
                                {String(tier.explanation)}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="mt-3 grid gap-2">
                        {guardEvaluation.stages.map(
                          (stage: {
                            name: string;
                            status: string;
                            detail: string;
                          }) => (
                            <div
                              className="flex items-start justify-between gap-4 rounded bg-white p-3 text-xs"
                              key={stage.name}
                            >
                              <div>
                                <div className="font-mono font-semibold">
                                  {stage.name}
                                </div>
                                <div className="mt-1 text-[var(--ink-muted)]">
                                  {stage.detail}
                                </div>
                              </div>
                              <StatusBadge value={stage.status} />
                            </div>
                          ),
                        )}
                      </div>
                    </>
                  ) : (
                    <p className="mt-2 text-sm text-[var(--ink-muted)]">
                      No V2 evidence exists for this trace.
                    </p>
                  )}
                </div>
              </div>

              <div className="border-t border-[var(--border)] bg-[var(--surface-low)] p-4 text-xs leading-5 text-[var(--ink-muted)]">
                Event source: {state.event_source}.{" "}
                {guardEvaluation
                  ? observeOnly
                    ? `V2 recommendation owner: ${guardEvaluation.enforced_by}; execution was not controlled by V2.`
                    : `Decision owner: ${guardEvaluation.enforced_by}.`
                  : "This historical trace predates the V2 evaluation event."}
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center p-8 text-center text-sm text-[var(--ink-muted)]">
              Decision details will appear here when a connected agent proposes a tool call.
            </div>
          )}
        </section>

        <section className="panel min-h-0 overflow-hidden">
          <div className="flex h-13 items-center gap-2 border-b border-[var(--border)] px-5">
            <Search size={16} className="text-blue-600" />
            <h2 className="eyebrow text-[var(--ink)]">Decision Evidence</h2>
          </div>
          <div className="h-[calc(100%-52px)] overflow-auto p-4 subtle-scrollbar">
            {!detail ? (
              <div className="flex h-full items-center justify-center text-sm text-[var(--ink-muted)]">
                No evidence selected.
              </div>
            ) : detail.precedents.length ? (
              <div className="space-y-3">
                {detail.precedents.map((precedent) => (
                  <div
                    className="rounded border border-[var(--border)] bg-[var(--surface-low)] p-4"
                    key={precedent.trace_id}
                  >
                    <div className="flex items-center justify-between">
                      <code className="text-xs font-semibold">
                        {precedent.tool_name}
                      </code>
                      <StatusBadge value={precedent.decision} />
                    </div>
                    <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
                      {precedent.intent}
                    </p>
                    <div className="mt-3 text-xs font-semibold text-blue-700">
                      {Math.round(precedent.risk_score * 100)} decision score
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded bg-[var(--surface-low)] p-4 text-sm">
                <AlertTriangle size={17} />
                No local precedents found.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function IntentValues({
  label,
  values,
  warning = false,
}: {
  label: string;
  values: unknown;
  warning?: boolean;
}) {
  const items = Array.isArray(values) ? values.map(String) : [];
  return (
    <div>
      <div className="text-[9px] font-bold uppercase tracking-wider text-[var(--ink-muted)]">
        {label}
      </div>
      {items.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {items.map((item) => (
            <code
              className={`rounded px-2 py-1 text-[10px] ${
                warning
                  ? "bg-[var(--red-bg)] text-[var(--red)]"
                  : "bg-[var(--surface-low)]"
              }`}
              key={item}
            >
              {item}
            </code>
          ))}
        </div>
      ) : (
        <div className="mt-1 text-[10px] text-[var(--ink-muted)]">None</div>
      )}
    </div>
  );
}
