import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import type { ReplayStep } from "../../api/types";
import { useProductionAgent } from "../../api/useProductionAgent";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";

export function TraceDetailPage() {
  const { id = "" } = useParams();
  const { agent, agentId, agents } = useProductionAgent();
  const session = useQuery({
    queryKey: ["session", agentId, id],
    queryFn: () => api.session(agentId, id),
    enabled: Boolean(agentId && id),
  });

  if (agents.isLoading || session.isLoading) return <LoadingState label="Loading session audit" />;
  if (agents.error || session.error) return <ErrorState message="Unable to load this session." />;
  if (!agent || !session.data || session.data.session.scenario_id !== null) {
    return (
      <div className="card">
        <EmptyState title="Session unavailable" message="No production trace was found." />
      </div>
    );
  }

  const detail = session.data;
  const counts = detail.steps.reduce(
    (current, step) => {
      const decision = step.guard_evaluation?.recommendation ?? step.decision;
      current[decision] = (current[decision] ?? 0) + 1;
      return current;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="page" style={{ maxWidth: 1100, margin: "0 auto" }}>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <ArrowLeft size={15} />
        <Link to="/traces">Trace Explorer</Link>
        <span>/</span>
        <span className="mono" style={{ color: "white" }}>{id}</span>
      </nav>

      <section className="card session-header">
        <div className="row-between">
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <code style={{ color: "var(--brand-cyan)", fontSize: 17 }}>{id}</code>
            <span className="tag">{agent.name}</span>
            <StatusChip value={detail.session.final_decision} />
            <span className="mono" style={{ color: "var(--text-muted)", fontSize: 11 }}>
              {formatDuration(detail.session.started_at, detail.session.updated_at)}
            </span>
          </div>
        </div>
        <div className="session-prompt">“{detail.session.user_intent}”</div>
        <div className="tag-list">
          <span className="tag">{detail.session.step_count} tool calls</span>
          <StatusChip value="allow" label={`${counts.allow ?? 0} allowed`} />
          <StatusChip value="block" label={`${counts.block ?? 0} blocked`} />
          <StatusChip
            value="require_approval"
            label={`${counts.require_approval ?? 0} approval`}
          />
        </div>
        <details className="card" style={{ marginTop: 16 }}>
          <summary
            className="row-between"
            style={{ cursor: "pointer", padding: 14, fontWeight: 600 }}
          >
            AgentGuard Analysis
            <ChevronDown size={16} />
          </summary>
          <div className="detail-block" style={{ color: "var(--text-secondary)", fontSize: 13 }}>
            Maximum session risk was {Math.round(detail.session.max_risk_score * 100)}%.
            The enforced result was {detail.session.final_decision.replaceAll("_", " ")}.
          </div>
        </details>
      </section>

      <section>
        <h2 style={{ margin: "0 0 18px", fontSize: 18 }}>
          Execution Timeline ({detail.steps.length})
        </h2>
        <div className="timeline">
          {detail.steps.map((step) => (
            <TimelineStep key={step.trace_id} step={step} />
          ))}
        </div>
      </section>
    </div>
  );
}

function TimelineStep({ step }: { step: ReplayStep }) {
  const evaluation = step.guard_evaluation;
  const decision = evaluation?.recommendation ?? step.decision;
  const normalized = evaluation?.normalized_action as
    | { operation?: string; capabilities?: string[] }
    | null;
  return (
    <article
      className="card timeline-step"
      style={{
        borderColor:
          decision === "block"
            ? "rgb(239 68 68 / 40%)"
            : decision === "require_approval"
              ? "rgb(245 158 11 / 40%)"
              : "var(--border)",
      }}
    >
      <span
        className="step-number"
        style={{
          borderColor:
            decision === "block"
              ? "var(--block)"
              : decision === "require_approval"
                ? "var(--approval)"
                : "var(--allow)",
        }}
      >
        {step.step_index}
      </span>
      <div className="row-between" style={{ alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <code style={{ color: "white", fontWeight: 600 }}>{step.tool_name}</code>
            <span style={{ color: "var(--text-muted)" }}>→</span>
            <code className="tag">{normalized?.operation ?? step.tool_category}</code>
          </div>
          <div
            className="mono"
            style={{
              marginTop: 12,
              borderLeft: "2px solid var(--border-strong)",
              background: "var(--background)",
              padding: "8px 10px",
              color: "#d1d5db",
              fontSize: 11,
            }}
          >
            {step.argument_summary}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <StatusChip value={decision} />
          <span className="mono" style={{ color: "var(--text-muted)", fontSize: 10 }}>
            {evaluation?.tier_results?.reduce(
              (sum, tier) => sum + Number(tier.latency_ms ?? 0),
              0,
            ) ?? 0}ms
          </span>
        </div>
      </div>
      {decision !== "allow" && (
        <div
          className="alert"
          style={{
            marginTop: 12,
            borderColor:
              decision === "block"
                ? "rgb(239 68 68 / 35%)"
                : "rgb(245 158 11 / 35%)",
            background:
              decision === "block" ? "var(--block-bg)" : "var(--approval-bg)",
            color: decision === "block" ? "var(--block)" : "var(--approval)",
          }}
        >
          {evaluation?.explanation ?? step.explanation}
        </div>
      )}
    </article>
  );
}

function formatDuration(start: string, end: string) {
  const seconds = Math.max(
    0,
    Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000),
  );
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}
