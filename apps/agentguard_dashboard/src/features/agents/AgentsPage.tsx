import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bot,
  CheckCircle2,
  Clock3,
  KeyRound,
  Plus,
  RadioTower,
} from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function AgentsPage() {
  const agents = useQuery({ queryKey: ["agents"], queryFn: api.agents });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });

  if (agents.isLoading || me.isLoading) {
    return <LoadingState label="Loading registered agents" />;
  }
  if (agents.error || me.error) {
    return (
      <ErrorState message="The AgentGuard API is offline. Start the full demo with `make demo`; the dashboard pages remain available from the sidebar." />
    );
  }

  return (
    <div className="space-y-5">
      <section className="panel flex items-center justify-between p-5">
        <div>
          <div className="eyebrow">Workspace</div>
          <h2 className="mt-2 text-xl font-bold">
            {me.data?.workspace.name}
          </h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Signed in as {me.data?.user.name} · {me.data?.user.role}
          </p>
        </div>
        <button
          className="flex items-center gap-2 rounded bg-black px-4 py-2.5 text-xs font-semibold text-white opacity-60"
          title="Registration is shown for product context; this demo uses one seeded agent."
        >
          <Plus size={15} />
          Register Agent
        </button>
      </section>

      <div className="grid gap-4">
        {agents.data?.items.map((agent) => {
          const deployment = agent.deployments[0];
          return (
            <article className="panel overflow-hidden" key={agent.agent_id}>
              <div className="flex items-start justify-between border-b border-[var(--border)] p-5">
                <Link
                  className="flex flex-1 gap-4 rounded focus:outline-none focus:ring-2 focus:ring-[var(--blue)]"
                  to={`/agents/${agent.agent_id}`}
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded bg-black text-white">
                    <Bot size={22} />
                  </div>
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-bold">{agent.name}</h3>
                      <StatusBadge value={agent.status} />
                    </div>
                    <p className="mt-2 max-w-2xl text-sm text-[var(--ink-muted)]">
                      {agent.description}
                    </p>
                    <code className="mt-3 block text-[11px] text-[var(--ink-muted)]">
                      {agent.agent_id}
                    </code>
                  </div>
                </Link>
                <div className="flex items-center gap-2">
                  <Link
                    className="rounded border border-[var(--border)] bg-white px-4 py-2 text-xs font-semibold"
                    to={`/agents/${agent.agent_id}`}
                  >
                    View Agent
                  </Link>
                <Link
                  className="rounded bg-[var(--blue)] px-4 py-2 text-xs font-semibold text-white"
                  to={`/agents/${agent.agent_id}/live`}
                >
                  Open Dashboard
                </Link>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-px bg-[var(--border)]">
                <AgentMetric
                  icon={<RadioTower size={16} />}
                  label="Framework"
                  value="Google ADK"
                />
                <AgentMetric
                  icon={<Activity size={16} />}
                  label="Environment"
                  value={deployment?.environment ?? "development"}
                />
                <AgentMetric
                  icon={<CheckCircle2 size={16} />}
                  label="Integration"
                  value="Callback configured"
                />
                <AgentMetric
                  icon={<Clock3 size={16} />}
                  label="Last heartbeat"
                  value={new Date(agent.last_seen_at).toLocaleString()}
                />
              </div>

              <div className="flex items-center justify-between bg-[var(--surface-low)] px-5 py-3 text-xs">
                <div className="flex items-center gap-2 text-[var(--ink-muted)]">
                  <KeyRound size={14} />
                  Integration credential configured for{" "}
                  <code>{deployment?.runtime_agent_name}</code>
                </div>
                <div>
                  Policy: <code>{agent.default_policy_id}</code>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function AgentMetric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-white p-4">
      <div className="flex items-center gap-2 text-[var(--ink-muted)]">
        {icon}
        <span className="eyebrow">{label}</span>
      </div>
      <div className="mt-2 text-sm font-semibold">{value}</div>
    </div>
  );
}
