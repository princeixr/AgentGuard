import {
  BarChart3,
  Boxes,
  Clock3,
  Settings,
  Shield,
  ShieldCheck,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useLocation, useParams } from "react-router-dom";

import { api } from "../api/client";

export function AppShell() {
  const location = useLocation();
  const { agentId } = useParams();
  const selectedAgentId = agentId ?? "";
  const agent = useQuery({
    queryKey: ["agent", selectedAgentId],
    queryFn: () => api.agent(selectedAgentId),
    enabled: Boolean(selectedAgentId),
  });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const navigation = selectedAgentId ? [
    {
      to: `/agents/${selectedAgentId}/summary`,
      label: "Agent Summary",
      icon: BarChart3,
    },
    {
      to: `/agents/${selectedAgentId}/sessions`,
      label: "Session History",
      icon: Clock3,
    },
    {
      to: `/agents/${selectedAgentId}/trace-interception`,
      label: "Trace Interception",
      icon: Shield,
    },
    {
      to: `/agents/${selectedAgentId}/guard`,
      label: "Guard Admin",
      icon: ShieldCheck,
    },
  ] : [];
  const pageTitle = location.pathname === "/agents"
    ? "Agents"
    : location.pathname === "/approvals"
      ? "Agents"
    : /^\/agents\/[^/]+$/.test(location.pathname)
      ? "Agent Details"
    : location.pathname.endsWith("/trace-interception") ||
        location.pathname.endsWith("/live")
      ? "Trace Interception"
      : location.pathname.endsWith("/sessions")
        ? "Session History"
        : location.pathname.endsWith("/summary")
          ? "Agent Summary"
      : location.pathname.endsWith("/replay") ||
          location.pathname.endsWith("/memory")
        ? "Trace Interception"
        : location.pathname.endsWith("/operations")
          ? "Agent Summary"
            : location.pathname.endsWith("/guard")
              ? "Guard Admin"
            : "AgentGuard";

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex w-[280px] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface-low)]">
        <div className="flex h-[72px] items-center gap-12 border-b border-[var(--border)] px-5">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-black text-white">
            <Shield size={21} strokeWidth={1.8} />
          </div>
          <div>
            <div className="text-[20px] font-bold leading-5">AgentGuard</div>
            <div className="mt-1 text-xs text-[var(--ink-muted)]">
              Runtime Security
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-2 p-3 pt-5">
          <NavLink
            to="/agents"
            className={({ isActive }) =>
              [
                "flex items-center gap-3 rounded px-4 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "bg-[var(--blue)] text-white"
                  : "text-[#333] hover:bg-[var(--surface-highest)]",
              ].join(" ")
            }
          >
            <Boxes size={18} />
            Agents
          </NavLink>
          <div className="px-4 pb-1 pt-4">
            <div className="eyebrow">Selected agent</div>
            <div className="mt-2 truncate text-sm font-semibold">
              {agent.data?.name ?? "No agent selected"}
            </div>
          </div>
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded px-4 py-3 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-[var(--blue)] text-white"
                    : "text-[#333] hover:bg-[var(--surface-highest)]",
                ].join(" ")
              }
            >
              <Icon size={18} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-[var(--border)] p-4">
          <div className="flex items-center gap-3 px-3 py-2 text-sm text-[var(--ink-muted)]">
            <Settings size={17} /> Settings
          </div>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[72px] shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-6">
          <div>
            <h1 className="text-[21px] font-bold tracking-[-0.02em]">
              {pageTitle}
            </h1>
            {agentId && (
              <div className="mt-1 text-xs text-[var(--ink-muted)]">
                {agent.data?.name} ·{" "}
                {agent.data?.deployments[0]?.environment}
              </div>
            )}
          </div>
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-2 rounded border border-[var(--border)] bg-white px-3 py-2 text-xs font-semibold">
              <span
                className={`h-2 w-2 rounded-full ${
                  agent.data?.status === "live" ? "live-dot bg-red-600" : "bg-amber-500"
                }`}
              />
              {agent.data?.status === "live" ? "Live" : "Setup required"}
            </div>
            <Settings size={20} />
            <div className="border-l border-[var(--border)] pl-4 text-right">
              <div className="text-xs font-semibold">
                {me.data?.user.name ?? "Operator"}
              </div>
              <div className="text-[10px] text-[var(--ink-muted)]">
                Workspace
              </div>
            </div>
          </div>
        </header>
        <div className="min-h-0 flex-1 overflow-auto p-6 subtle-scrollbar">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
