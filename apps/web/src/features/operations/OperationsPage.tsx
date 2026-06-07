import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Ban,
  Clock3,
  Download,
  RadioTower,
} from "lucide-react";
import { useParams } from "react-router-dom";

import { api } from "../../api/client";
import { Chart } from "../../components/Chart";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function OperationsPage() {
  const { agentId = "" } = useParams();
  const operations = useQuery({
    queryKey: ["operations", agentId],
    queryFn: () => api.operations(agentId),
  });

  if (operations.isLoading) return <LoadingState label="Loading operations" />;
  if (operations.error || !operations.data) {
    return <ErrorState message="Unable to load operations metrics." />;
  }

  const data = operations.data;
  const toolChart = {
    animation: false,
    grid: { left: 95, right: 25, top: 10, bottom: 20 },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "#ebe7e6" } } },
    yAxis: {
      type: "category",
      data: data.riskiest_tools.map((item) => item.name),
      axisLabel: { fontFamily: "monospace", fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        data: data.riskiest_tools.map((item) => item.count),
        itemStyle: { color: "#246fdc", borderRadius: [0, 2, 2, 0] },
        barWidth: 14,
      },
    ],
    tooltip: { trigger: "axis" },
  };
  const failureChart = {
    animation: false,
    tooltip: { trigger: "item" },
    legend: {
      orient: "vertical",
      right: 0,
      top: "center",
      formatter: (name: string) => name.replaceAll("_", " "),
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["45%", "70%"],
        center: ["32%", "52%"],
        label: { show: false },
        data: data.failure_modes.map((item, index) => ({
          name: item.name,
          value: item.count,
          itemStyle: {
            color: ["#1c1b1b", "#7d7f7f", "#c7c9c9", "#c62828"][index % 4],
          },
        })),
      },
    ],
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm text-[var(--ink-muted)]">
          <Clock3 size={16} />
          Deterministic demo dataset
        </div>
        <a
          className="flex items-center gap-2 rounded border border-[var(--border)] bg-white px-3 py-2 text-xs font-semibold"
          href={`/api/v1/agents/${encodeURIComponent(agentId)}/operations/export`}
        >
          <Download size={15} />
          Export
        </a>
      </div>

      <section className="grid grid-cols-4 gap-4">
        <MetricCard
          icon={<RadioTower size={18} />}
          label="Intercepted Calls"
          value={String(data.intercepted_calls)}
          detail={`${data.session_count} sessions`}
        />
        <MetricCard
          icon={<Ban size={18} />}
          label="Blocked Rate"
          value={`${(data.blocked_rate * 100).toFixed(1)}%`}
          detail={`${data.blocked_count} calls blocked`}
        />
        <MetricCard
          icon={<Clock3 size={18} />}
          label="Decision Latency"
          value={`${data.p95_latency_ms}ms`}
          detail={`p50 ${data.p50_latency_ms}ms`}
        />
        <MetricCard
          icon={<Activity size={18} />}
          label="Intervention Rate"
          value={`${(data.intervention_rate * 100).toFixed(1)}%`}
          detail={`${data.intervention_count} interventions`}
        />
      </section>

      <section className="grid grid-cols-2 gap-4">
        <div className="panel p-5">
          <h2 className="text-sm font-bold">Riskiest Tools</h2>
          <div className="mt-3 border-t border-[var(--border)] pt-3">
            <Chart option={toolChart} style={{ height: 220 }} />
          </div>
        </div>
        <div className="panel p-5">
          <h2 className="text-sm font-bold">Failure Modes</h2>
          <div className="mt-3 border-t border-[var(--border)] pt-3">
            <Chart option={failureChart} style={{ height: 220 }} />
          </div>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="flex h-14 items-center justify-between border-b border-[var(--border)] px-5">
          <h2 className="text-sm font-bold">System Health</h2>
          <span className="text-xs text-[var(--ink-muted)]">Live status</span>
        </div>
        <div>
          <div className="grid grid-cols-[1fr_180px_1fr] bg-[var(--surface-container)] px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--ink-muted)]">
            <span>Service component</span>
            <span>Status</span>
            <span>Detail</span>
          </div>
          {data.health.map((component) => (
            <div
              className="grid grid-cols-[1fr_180px_1fr] items-center border-t border-[var(--border)] px-5 py-4 text-sm"
              key={component.name}
            >
              <span className="font-medium">{component.name}</span>
              <span>
                <StatusBadge value={component.status} />
              </span>
              <span className="text-xs text-[var(--ink-muted)]">
                {component.detail}
              </span>
            </div>
          ))}
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
      <div className="mt-3 text-3xl font-bold tracking-[-0.03em]">{value}</div>
      <div className="mt-2 text-xs text-[var(--ink-muted)]">{detail}</div>
    </div>
  );
}
