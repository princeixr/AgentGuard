import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  Search,
  ShieldAlert,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import { useLiveEvents } from "../../api/useLiveEvents";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function LiveInterceptionPage() {
  const { agentId = "" } = useParams();
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
  if (interception.isLoading) {
    return <LoadingState label="Loading interception console" />;
  }
  if (interception.error) {
    return <ErrorState message="The interception API is unavailable." />;
  }

  const state = interception.data!;
  const detail = state.detail;
  const v2Event = detail?.events.find(
    (event) => event.event_type === "firewall_v2_evaluated",
  );
  const v2Evaluation = v2Event?.payload?.evaluation;
  const v2Enforced = v2Event?.payload?.enforced_by === "firewall_v2";
  const normalizedAction = v2Evaluation?.normalized_action;
  const policyEvaluation = v2Evaluation?.policy_evaluation;
  const currentV2Decision =
    detail?.item.v2_effective_decision ??
    detail?.item.v2_recommendation ??
    policyEvaluation?.recommendation;
  const displayedDecision = currentV2Decision ?? detail?.item.decision;
  const decisionOwner = v2Evaluation
    ? v2Enforced
      ? "FirewallV2 enforced decision"
      : "FirewallV2 shadow recommendation"
    : "FirewallV1 decision";
  const displayedExplanation =
    policyEvaluation?.explanation ?? detail?.item.explanation;
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
                "Run the selected Google ADK agent to inspect its tool calls."}
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
            Run Agent Test
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
                  Run the Google ADK agent from its Agent Details page. Real
                  tool proposals and AgentGuard decisions will stream here.
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
                {visibleSteps.map((step) => (
                  <div
                    className={`relative rounded border p-4 ${
                      step.trace_id === state.current_trace_id
                        ? "border-amber-400 bg-amber-50/60"
                        : "border-[var(--border)]"
                    }`}
                    key={step.trace_id}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <code className="text-xs font-semibold">
                          {step.tool_name}
                        </code>
                        <div className="mt-1 text-[9px] font-bold uppercase tracking-wider text-[var(--ink-muted)]">
                          {step.v2_enforcement_status
                            ? step.enforced_by === "firewall_v2"
                              ? "V2 enforced"
                              : "V2 recommendation"
                            : "V1 enforced"}
                        </div>
                      </div>
                      <StatusBadge
                        value={
                          step.v2_effective_decision ??
                          step.v2_recommendation ??
                          step.decision
                        }
                      />
                    </div>
                    <div className="mt-2 truncate mono text-[11px] text-[var(--ink-muted)]">
                      {step.argument_summary}
                    </div>
                    {step.v2_recommendation &&
                      step.enforced_by !== "firewall_v2" && (
                        <div className="mt-3 flex items-center justify-between border-t border-[var(--border)] pt-2 text-[10px]">
                          <span className="text-[var(--ink-muted)]">
                            V1 enforced
                          </span>
                          <StatusBadge value={step.v1_decision ?? step.decision} />
                        </div>
                      )}
                  </div>
                ))}
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
                  <StatusBadge value={displayedDecision} />
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
                    <div className="eyebrow">Authorized intent</div>
                    <p className="mt-2 text-sm leading-5">
                      {detail.trace.intent.normalized_intent}
                    </p>
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
                      {v2Evaluation
                        ? v2Enforced
                          ? "firewall_v2 · deterministic policy"
                          : "firewall_v2 · shadow"
                        : String(detail.decision.tier_used ?? "decision_policy")}
                    </code>
                  </div>
                  {policyEvaluation?.matched_rules?.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {policyEvaluation.matched_rules.map(
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
                      Current FirewallV2 interception
                    </div>
                    <StatusBadge
                      value={
                        v2Evaluation
                          ? v2Evaluation.enforcement_status.replace("_", " ")
                          : "not run"
                      }
                    />
                  </div>
                  {v2Evaluation ? (
                    <>
                      <p className="mt-2 text-sm leading-5">
                        {v2Evaluation.explanation}
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
                      {policyEvaluation && (
                        <div className="mt-3 rounded border border-blue-200 bg-white p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="eyebrow">Policy recommendation</div>
                              <code className="mt-1 block text-xs">
                                {policyEvaluation.policy_id}@
                                {policyEvaluation.policy_version}
                              </code>
                            </div>
                            <StatusBadge value={policyEvaluation.recommendation} />
                          </div>
                          <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
                            {policyEvaluation.explanation}
                          </p>
                          {policyEvaluation.matched_rules.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {policyEvaluation.matched_rules.map(
                                (rule: { rule_id: string; effect: string }) => (
                                  <code
                                    className="rounded bg-blue-50 px-2 py-1 text-[10px] font-semibold text-blue-800"
                                    key={rule.rule_id}
                                  >
                                    {rule.rule_id}: {rule.effect}
                                  </code>
                                ),
                              )}
                            </div>
                          )}
                          {policyEvaluation.deferred_rule_ids.length > 0 && (
                            <div className="mt-3 text-[11px] text-[var(--ink-muted)]">
                              Deferred until normalization:{" "}
                              {policyEvaluation.deferred_rule_ids.join(", ")}
                            </div>
                          )}
                        </div>
                      )}
                      <div className="mt-3 grid gap-2">
                        {v2Evaluation.stages.map(
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
                Event source: {state.event_source}. Enforcement is currently owned by
                {v2Enforced ? " FirewallV2 deterministic policy." : " FirewallV1."}{" "}
                {v2Enforced
                  ? "Intent, Tier 2, Tier 3, and approval resume are not active."
                  : "FirewallV2 evidence is observe-only in the current mode."}
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center p-8 text-center text-sm text-[var(--ink-muted)]">
              Decision details will appear here as the scenario runs.
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
                      {Math.round(precedent.risk_score * 100)} risk score
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
