import { useQuery } from "@tanstack/react-query";
import { Ban, CheckCircle2, ShieldAlert, Wrench } from "lucide-react";
import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { api } from "../../api/client";
import { Chart } from "../../components/Chart";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";

export function SecuritySummaryPage() {
  const { agentId = "" } = useParams();
  const operations = useQuery({
    queryKey: ["operations", agentId],
    queryFn: () => api.operations(agentId),
  });
  const sessions = useQuery({
    queryKey: ["sessions", agentId],
    queryFn: () => api.sessions(agentId),
  });
  const memory = useQuery({
    queryKey: ["memory", agentId, "summary"],
    queryFn: () => api.memory(agentId, new URLSearchParams({ page_size: "200" })),
  });

  if (operations.isLoading || sessions.isLoading || memory.isLoading) {
    return <LoadingState label="Loading security posture summary" />;
  }
  if (
    operations.error ||
    sessions.error ||
    memory.error ||
    !operations.data ||
    !sessions.data ||
    !memory.data
  ) {
    return <ErrorState message="Unable to load security summary data." />;
  }

  const traces = memory.data.items;
  const decisionCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const trace of traces) {
      counts.set(trace.decision, (counts.get(trace.decision) ?? 0) + 1);
    }
    return counts;
  }, [traces]);

  const featureCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const trace of traces) {
      for (const label of trace.labels) {
        counts.set(label, (counts.get(label) ?? 0) + 1);
      }
    }
    return counts;
  }, [traces]);

  const importantFeatures = [
    "intent_drift",
    "scope_creep",
    "malicious_command",
  ].map((feature) => ({
    feature,
    count: featureCounts.get(feature) ?? 0,
  }));

  const topFeatures = [...featureCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const decisionChart = {
    animation: false,
    tooltip: { trigger: "item" },
    legend: { top: "bottom", textStyle: { fontSize: 11 } },
    series: [
      {
        type: "pie",
        radius: ["35%", "70%"],
        center: ["50%", "45%"],
        data: [...decisionCounts.entries()].map(([name, value], index) => ({
          name: name.replaceAll("_", " "),
          value,
          itemStyle: {
            color: ["#0f8a55", "#246fdc", "#c56a00", "#c62828", "#7d7f7f"][index % 5],
          },
        })),
      },
    ],
  };
  const featuresChart = {
    animation: false,
    grid: { left: 115, right: 20, top: 10, bottom: 20 },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "#ebe7e6" } } },
    yAxis: {
      type: "category",
      data: topFeatures.map(([name]) => name.replaceAll("_", " ")),
      axisLabel: { fontSize: 10 },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        type: "bar",
        data: topFeatures.map(([, count]) => count),
        barWidth: 14,
        itemStyle: { color: "#246fdc", borderRadius: [0, 2, 2, 0] },
      },
    ],
  };

  const blocked = decisionCounts.get("block") ?? 0;
  const allowed = decisionCounts.get("allow") ?? 0;
  const approvalRequired = decisionCounts.get("require_approval") ?? 0;
  const posture =
    blocked > approvalRequired
      ? "High intervention pressure"
      : operations.data.blocked_rate > 0.2
        ? "Elevated risk posture"
        : "Stable guard posture";

  return (
    <div className="space-y-4">
      <section className="grid grid-cols-4 gap-4">
        <MetricCard
          icon={<Wrench size={17} />}
          label="Intercepted Calls"
          value={String(operations.data.intercepted_calls)}
          detail={`${operations.data.session_count} sessions observed`}
        />
        <MetricCard
          icon={<Ban size={17} />}
          label="Blocked"
          value={String(blocked)}
          detail={`${(operations.data.blocked_rate * 100).toFixed(1)}% block rate`}
        />
        <MetricCard
          icon={<ShieldAlert size={17} />}
          label="Approval Required"
          value={String(approvalRequired)}
          detail="Calls requiring human decision"
        />
        <MetricCard
          icon={<CheckCircle2 size={17} />}
          label="Allowed"
          value={String(allowed)}
          detail={posture}
        />
      </section>

      <section className="grid grid-cols-2 gap-4">
        <div className="panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold">Historical Decision Split</h2>
            <span className="text-xs text-[var(--ink-muted)]">
              {traces.length} latest traces
            </span>
          </div>
          <div className="mt-3 border-t border-[var(--border)] pt-3">
            <Chart option={decisionChart} style={{ height: 250 }} />
          </div>
        </div>
        <div className="panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold">Detected Security Features</h2>
            <span className="text-xs text-[var(--ink-muted)]">
              Label frequency
            </span>
          </div>
          <div className="mt-3 border-t border-[var(--border)] pt-3">
            <Chart option={featuresChart} style={{ height: 250 }} />
          </div>
        </div>
      </section>

      <section className="panel p-5">
        <h2 className="text-sm font-bold">Session-Level Guard Signals</h2>
        <div className="mt-4 grid grid-cols-3 gap-3">
          {importantFeatures.map((item) => (
            <div
              className="rounded border border-[var(--border)] bg-[var(--surface-low)] p-4"
              key={item.feature}
            >
              <div className="eyebrow">{item.feature.replaceAll("_", " ")}</div>
              <div className="mt-2 text-2xl font-bold">{item.count}</div>
              <div className="mt-1 text-xs text-[var(--ink-muted)]">
                traces tagged in recent history
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 text-xs text-[var(--ink-muted)]">
          Sessions analyzed: {sessions.data.length} · p95 decision latency:{" "}
          {operations.data.p95_latency_ms}ms
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
