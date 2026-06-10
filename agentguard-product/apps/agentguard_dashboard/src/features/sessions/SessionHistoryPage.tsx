import { useQuery } from "@tanstack/react-query";
import { Clock3, Hash, ShieldAlert, Wrench } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import { useLiveEvents } from "../../api/useLiveEvents";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

type SessionRow = {
  sessionId: string;
  updatedAt: string;
  stepCount: number;
  toolSequence: string[];
  maxRiskScore: number;
  decision: string;
  status: "live" | "past_call";
  to: string;
};

export function SessionHistoryPage() {
  const { agentId = "" } = useParams();
  const connected = useLiveEvents(agentId);
  const interception = useQuery({
    queryKey: ["interception", agentId],
    queryFn: () => api.currentInterception(agentId),
    refetchInterval: 1_000,
  });
  const sessions = useQuery({
    queryKey: ["sessions", agentId],
    queryFn: () => api.sessions(agentId),
    refetchInterval: 2_000,
  });

  if (sessions.isLoading || interception.isLoading) {
    return <LoadingState label="Loading session history" />;
  }
  if (sessions.error || !sessions.data) {
    return <ErrorState message="Unable to load session history." />;
  }
  if (interception.error || !interception.data) {
    return <ErrorState message="Unable to load live interception state." />;
  }

  const archivedRows: SessionRow[] = sessions.data.map((session) => ({
    sessionId: session.session_id,
    updatedAt: session.updated_at,
    stepCount: session.step_count,
    toolSequence: session.tool_sequence,
    maxRiskScore: session.max_risk_score,
    decision: session.final_decision,
    status: "past_call" as const,
    to: `/agents/${agentId}/trace-interception?sessionId=${encodeURIComponent(session.session_id)}`,
  }));
  const liveState = interception.data;
  const isLiveSession =
    Boolean(liveState.session_id) &&
    liveState.status !== "idle" &&
    liveState.status !== "completed";
  const activeSessionId = liveState.session_id ?? null;
  const liveRow: SessionRow | null = isLiveSession && activeSessionId ? {
    sessionId: activeSessionId,
    updatedAt:
      liveState.detail?.item.timestamp ?? new Date().toISOString(),
    stepCount: Math.max(liveState.current_step, 1),
    toolSequence: liveState.detail?.item.tool_name
      ? [liveState.detail.item.tool_name]
      : [],
    maxRiskScore: liveState.detail?.item.risk_score ?? 0,
    decision: liveState.detail?.item.decision ?? "review",
    status: "live" as const,
    to: `/agents/${agentId}/trace-interception`,
  } : null;

  const rows: SessionRow[] = [...archivedRows]
    .filter((row) => row.sessionId !== activeSessionId)
    .sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    );
  if (liveRow) {
    rows.unshift(liveRow);
  }

  const toolCalls = rows.reduce((count, session) => count + session.stepCount, 0);
  const uniqueTools = new Set(rows.flatMap((session) => session.toolSequence));
  const riskySessions = rows.filter((session) =>
    ["block", "require_approval", "review"].includes(session.decision)
  );
  const liveSessions = rows.filter((session) => session.status === "live").length;

  return (
    <div className="space-y-4">
      <section className="grid grid-cols-4 gap-4">
        <MetricCard
          icon={<Hash size={16} />}
          label="Sessions"
          value={String(rows.length)}
          detail="Captured runtime conversations"
        />
        <MetricCard
          icon={<Wrench size={16} />}
          label="Tool Calls"
          value={String(toolCalls)}
          detail="Total intercepted trace records"
        />
        <MetricCard
          icon={<Clock3 size={16} />}
          label="Unique Tools"
          value={String(uniqueTools.size)}
          detail="Distinct tool names observed"
        />
        <MetricCard
          icon={<ShieldAlert size={16} />}
          label="Live Sessions"
          value={String(liveSessions)}
          detail={`${riskySessions.length} high-risk sessions`}
        />
      </section>

      <section className="panel min-h-0 overflow-hidden">
        <div className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--surface-low)] px-5 py-2">
          <span className="text-xs text-[var(--ink-muted)]">
            {connected ? "Live updates connected" : "Polling updates every second"}
          </span>
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-amber-500"}`}
          />
        </div>
        <div className="grid grid-cols-[220px_110px_180px_110px_1fr_140px_120px] bg-[var(--surface-container)] px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--ink-muted)]">
          <span>Session ID</span>
          <span>Status</span>
          <span>Last Updated</span>
          <span>Tool Calls</span>
          <span>Tool Names</span>
          <span>Max Risk</span>
          <span>Decision</span>
        </div>
        <div className="max-h-[70vh] overflow-auto subtle-scrollbar">
          {rows.length === 0 ? (
            <div className="p-6 text-sm text-[var(--ink-muted)]">
              No sessions found for this agent yet.
            </div>
          ) : (
            rows.map((session) => (
              <Link
                className="grid grid-cols-[220px_110px_180px_110px_1fr_140px_120px] items-center border-t border-[var(--border)] px-5 py-4 text-sm hover:bg-[var(--surface-low)]"
                key={session.sessionId}
                to={session.to}
              >
                <code className="truncate text-xs font-semibold">
                  {session.sessionId}
                </code>
                <span>
                  <StatusBadge value={session.status} />
                </span>
                <span className="mono text-[11px] text-[var(--ink-muted)]">
                  {new Date(session.updatedAt).toLocaleString()}
                </span>
                <span className="text-sm font-semibold">{session.stepCount}</span>
                <div className="flex flex-wrap gap-1.5 py-1">
                  {session.toolSequence.slice(0, 4).map((tool) => (
                    <code
                      className="rounded border border-[var(--border)] bg-[var(--surface-low)] px-2 py-1 text-[10px]"
                      key={`${session.sessionId}:${tool}`}
                    >
                      {tool}
                    </code>
                  ))}
                  {session.toolSequence.length > 4 && (
                    <span className="text-xs text-[var(--ink-muted)]">
                      +{session.toolSequence.length - 4} more
                    </span>
                  )}
                </div>
                <span className="mono text-xs">{session.maxRiskScore.toFixed(2)}</span>
                <span>
                  <StatusBadge value={session.decision} />
                </span>
              </Link>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  detail,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <span className="eyebrow text-[var(--ink)]">{label}</span>
        <span className="text-[var(--ink-muted)]">{icon}</span>
      </div>
      <div className="mt-2 text-3xl font-bold tracking-[-0.03em]">{value}</div>
      <div className="mt-2 text-xs text-[var(--ink-muted)]">{detail}</div>
    </div>
  );
}
