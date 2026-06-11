import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import type { Decision } from "../../api/types";
import { useProductionAgent } from "../../api/useProductionAgent";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";

type Filter = "all" | "active" | "complete" | "blocks" | "approval";

export function TracesPage() {
  const navigate = useNavigate();
  const { agent, agentId, agents } = useProductionAgent();
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const sessions = useQuery({
    queryKey: ["sessions", agentId],
    queryFn: () => api.sessions(agentId),
    enabled: Boolean(agentId),
    refetchInterval: 5_000,
  });

  const rows = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (sessions.data ?? [])
      .filter((session) => session.scenario_id === null)
      .filter((session) => {
        if (filter === "blocks") return session.final_decision === "block";
        if (filter === "approval") return session.final_decision === "require_approval";
        if (filter === "active") return isActive(session.updated_at);
        if (filter === "complete") return !isActive(session.updated_at);
        return true;
      })
      .filter(
        (session) =>
          !query ||
          session.session_id.toLowerCase().includes(query) ||
          session.user_intent.toLowerCase().includes(query) ||
          session.tool_sequence.join(" ").toLowerCase().includes(query),
      );
  }, [filter, search, sessions.data]);

  if (agents.isLoading) return <LoadingState label="Loading trace explorer" />;
  if (agents.error) return <ErrorState message="Unable to load connected agents." />;
  if (!agent) {
    return (
      <div className="card">
        <EmptyState title="No connected agent" message="No production sessions are available." />
      </div>
    );
  }

  return (
    <div className="page">
      <section className="card filters">
        <div className="filter-buttons">
          {[
            ["all", "All Sessions"],
            ["active", "Active"],
            ["complete", "Complete"],
            ["blocks", "Has Blocks"],
            ["approval", "Has Pending"],
          ].map(([value, label]) => (
            <button
              className={`filter-button ${filter === value ? "filter-button-active" : ""}`}
              key={value}
              onClick={() => setFilter(value as Filter)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <label style={{ position: "relative", width: 270 }}>
          <Search
            size={16}
            style={{ left: 10, position: "absolute", top: 9, color: "var(--text-muted)" }}
          />
          <input
            className="input"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search sessions…"
            style={{ paddingLeft: 34 }}
            value={search}
          />
        </label>
      </section>

      <section className="card table-wrap" style={{ flex: 1 }}>
        {sessions.isLoading ? (
          <LoadingState label="Loading sessions" />
        ) : rows.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Started</th>
                <th>Session ID</th>
                <th>Agent</th>
                <th>User Query</th>
                <th>Traces</th>
                <th>Risk</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((session) => (
                <tr
                  key={session.session_id}
                  onClick={() => navigate(`/traces/${encodeURIComponent(session.session_id)}`)}
                  style={{ cursor: "pointer" }}
                >
                  <td className="mono">{formatTime(session.started_at)}</td>
                  <td className="mono" style={{ color: "var(--brand-cyan)" }}>
                    {session.session_id}
                  </td>
                  <td>{agent.name}</td>
                  <td style={{ maxWidth: 440, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {session.user_intent}
                  </td>
                  <td className="mono">{session.step_count}</td>
                  <td>
                    <StatusChip
                      value={session.final_decision}
                      label={riskLabel(session.final_decision, session.max_risk_score)}
                    />
                  </td>
                  <td>
                    <span style={{ color: "var(--text-secondary)" }}>
                      {isActive(session.updated_at) ? "Active" : "Complete"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState
            title="No production sessions"
            message="Session traces will appear after live SDK traffic is evaluated."
          />
        )}
      </section>
    </div>
  );
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour12: false });
}

function isActive(value: string) {
  return Date.now() - new Date(value).getTime() < 60_000;
}

function riskLabel(decision: Decision, risk: number) {
  if (decision === "block") return `${Math.round(risk * 100)}% blocked`;
  if (decision === "require_approval") return "approval";
  return `${Math.round(risk * 100)}% risk`;
}
