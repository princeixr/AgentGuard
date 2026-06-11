import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bot, Clock3, Tag } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { Agent } from "../../api/types";
import { useProductionAgent } from "../../api/useProductionAgent";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";

export function OverviewPage() {
  const { agents, productionAgents, agent, agentId } = useProductionAgent();
  const operations = useQuery({
    queryKey: ["operations", agentId],
    queryFn: () => api.operations(agentId),
    enabled: Boolean(agentId),
    refetchInterval: 5_000,
  });
  const memory = useQuery({
    queryKey: ["memory", agentId, "overview"],
    queryFn: () => api.memory(agentId, new URLSearchParams({ page_size: "8" })),
    enabled: Boolean(agentId),
    refetchInterval: 5_000,
  });

  if (agents.isLoading) return <LoadingState label="Loading connected agents" />;
  if (agents.error) return <ErrorState message="Unable to load connected agents." />;

  const productionActivity =
    memory.data?.items.filter((item) => item.scenario_id === null) ?? [];

  return (
    <div className="page">
      <section className="page-heading">
        <div>
          <h2>Connected Agents</h2>
          <p>Monitoring and governance for active agent deployments.</p>
        </div>
      </section>

      <section className="stats-grid">
        <Metric
          label="Total Interceptions"
          value={operations.data?.intercepted_calls ?? 0}
        />
        <Metric
          label="Block Rate"
          value={`${((operations.data?.blocked_rate ?? 0) * 100).toFixed(1)}%`}
        />
        <Metric
          label="P50 Evaluation Latency"
          value={`${operations.data?.p50_latency_ms ?? 0}ms`}
        />
      </section>

      <section>
        {productionAgents.length ? (
          <div style={{ display: "grid", gap: 16 }}>
            {productionAgents.map((item) => (
              <AgentCard agent={item} key={item.agent_id} />
            ))}
          </div>
        ) : (
          <div className="card">
            <EmptyState
              title="No agents connected"
              message="Agents appear here after registering through the AgentGuard SDK."
            />
          </div>
        )}
      </section>

      <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <h3 className="section-title">Recent Interceptions</h3>
        <div className="card table-wrap">
          {memory.isLoading ? (
            <LoadingState label="Loading interception history" />
          ) : productionActivity.length ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Agent</th>
                  <th>Tool</th>
                  <th>Domain</th>
                  <th>Decision</th>
                </tr>
              </thead>
              <tbody>
                {productionActivity.map((item) => (
                  <tr key={item.trace_id}>
                    <td className="mono">{formatTimestamp(item.timestamp)}</td>
                    <td>{agent?.name ?? item.agent_id}</td>
                    <td className="mono" style={{ color: "var(--brand-cyan)" }}>
                      {item.tool_name}
                    </td>
                    <td>{item.domain}</td>
                    <td>
                      <StatusChip value={item.decision} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState
              title="No production interceptions yet"
              message="Live SDK decisions will appear here as agents submit tool proposals."
            />
          )}
        </div>
      </section>
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const definition = useQuery({
    queryKey: ["agent-definition", agent.agent_id],
    queryFn: () => api.agentDefinition(agent.agent_id),
  });
  const operations = useQuery({
    queryKey: ["operations", agent.agent_id],
    queryFn: () => api.operations(agent.agent_id),
    refetchInterval: 5_000,
  });

  const capabilities = Array.from(
    new Set(definition.data?.tools.flatMap((tool) => tool.capabilities) ?? []),
  ).slice(0, 8);

  return (
    <article className="card agent-card">
      <div className="agent-card-header">
        <div className="agent-identity">
          <div className="agent-icon">
            <Bot size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className="agent-name">{agent.name}</span>
              <StatusChip value={agent.status} label={agent.status} />
            </div>
            <div className="meta-line">
              <span><Tag size={12} /> {agent.agent_id}</span>
              <span><Clock3 size={12} /> {formatRelative(agent.last_seen_at)}</span>
              <span>{agent.default_policy_id}</span>
            </div>
          </div>
        </div>
        <Link className="button" to="/live">
          View Live <ArrowRight size={14} />
        </Link>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0,1fr) auto",
          gap: 24,
          marginTop: 18,
          borderTop: "1px solid var(--border)",
          paddingTop: 16,
        }}
      >
        <div>
          <div className="eyebrow" style={{ marginBottom: 9 }}>Capabilities</div>
          <div className="tag-list">
            {capabilities.length ? (
              capabilities.map((capability) => (
                <span className="tag" key={capability}>{capability}</span>
              ))
            ) : (
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
                Manifest metadata unavailable
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          <AgentMetric label="Intercepted" value={operations.data?.intercepted_calls ?? 0} />
          <AgentMetric label="Interventions" value={operations.data?.intervention_count ?? 0} />
          <AgentMetric label="Blocked" value={operations.data?.blocked_count ?? 0} tone="block" />
        </div>
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card stat">
      <div className="eyebrow">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function AgentMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "block";
}) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div
        className="mono"
        style={{
          marginTop: 5,
          color: tone === "block" ? "var(--block)" : "white",
          fontSize: 17,
          fontWeight: 600,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function formatTimestamp(value: string) {
  return new Date(value).toLocaleTimeString([], {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatRelative(value: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}
