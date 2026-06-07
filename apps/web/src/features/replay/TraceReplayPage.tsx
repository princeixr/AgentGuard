import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Database, User } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../../api/client";
import { Chart } from "../../components/Chart";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function TraceReplayPage() {
  const { agentId = "" } = useParams();
  const sessions = useQuery({
    queryKey: ["sessions", agentId],
    queryFn: () => api.sessions(agentId),
  });
  const [selected, setSelected] = useState("");

  useEffect(() => {
    if (!selected && sessions.data?.length) {
      const blocked =
        sessions.data.find((item) => item.final_decision === "block") ??
        sessions.data[0];
      setSelected(blocked.session_id);
    }
  }, [selected, sessions.data]);

  const detail = useQuery({
    queryKey: ["session", agentId, selected],
    queryFn: () => api.session(agentId, selected),
    enabled: Boolean(selected),
  });

  const chartOption = useMemo(
    () => ({
      animation: false,
      grid: { left: 38, right: 18, top: 25, bottom: 35 },
      xAxis: {
        type: "category",
        data: detail.data?.steps.map((step) =>
          step.tool_name.replace(/^gmail_/, ""),
        ),
        axisLine: { lineStyle: { color: "#bdb9b7" } },
        axisLabel: { color: "#646565", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 1,
        axisLabel: {
          formatter: (value: number) => Math.round(value * 100),
          color: "#646565",
        },
        splitLine: { lineStyle: { color: "#ebe7e6" } },
      },
      series: [
        {
          type: "line",
          data: detail.data?.steps.map((step) => step.risk_score),
          smooth: false,
          symbolSize: 10,
          lineStyle: { width: 2, color: "#1c1b1b" },
          itemStyle: {
            color: (params: { data: number }) =>
              params.data >= 0.5 ? "#c62828" : "#0f8a55",
          },
          areaStyle: { color: "rgba(198,40,40,0.05)" },
        },
      ],
      tooltip: { trigger: "axis", valueFormatter: (v: number) => `${Math.round(v * 100)}` },
    }),
    [detail.data],
  );

  if (sessions.isLoading) return <LoadingState label="Loading sessions" />;
  if (sessions.error) return <ErrorState message="Unable to load sessions." />;

  return (
    <div className="flex h-full min-h-[720px] flex-col gap-4">
      <div className="flex items-center gap-3">
        <label className="eyebrow">Session</label>
        <select
          className="rounded border border-[var(--border)] bg-white px-3 py-2 text-sm"
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
        >
          {sessions.data?.map((session) => (
            <option value={session.session_id} key={session.session_id}>
              {session.scenario_id} · {session.final_decision}
            </option>
          ))}
        </select>
      </div>

      {detail.isLoading ? (
        <LoadingState label="Building replay" />
      ) : detail.error || !detail.data ? (
        <ErrorState message="Unable to load the selected replay." />
      ) : (
        <div className="page-grid flex-1 grid-cols-[minmax(420px,0.95fr)_minmax(520px,1.1fr)]">
          <section className="panel min-h-0 overflow-hidden">
            <div className="flex h-14 items-center justify-between border-b border-[var(--border)] px-5">
              <h2 className="text-sm font-bold">Execution Timeline</h2>
              <StatusBadge value={detail.data.session.final_decision} />
            </div>
            <div className="h-[calc(100%-56px)] overflow-auto p-5 subtle-scrollbar">
              <div className="relative ml-4 border-l border-[var(--border)] pl-8">
                <TimelineCard
                  icon={<User size={17} />}
                  title="User Input Received"
                  body={detail.data.session.user_intent}
                />
                {detail.data.steps.map((step) => (
                  <TimelineCard
                    key={step.trace_id}
                    icon={
                      step.decision === "block" ? (
                        <AlertTriangle size={17} />
                      ) : step.tool_category === "file" ? (
                        <Database size={17} />
                      ) : (
                        <CheckCircle2 size={17} />
                      )
                    }
                    title={step.tool_name}
                    body={step.argument_summary}
                    decision={step.decision}
                    risk={step.risk_score}
                  />
                ))}
              </div>
            </div>
          </section>

          <div className="grid min-h-0 grid-rows-[auto_1fr_auto] gap-4">
            <section className="panel p-5">
              <div className="flex items-start justify-between gap-5">
                <div>
                  <h2 className="text-xl font-bold">
                    {detail.data.session.final_decision === "block"
                      ? "Unsafe Action Intercepted"
                      : "Session Completed"}
                  </h2>
                  <p className="mt-1 text-sm text-[var(--ink-muted)]">
                    {detail.data.steps.at(-1)?.explanation}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-4xl font-bold text-[var(--red)]">
                    {Math.round(detail.data.session.max_risk_score * 100)}
                  </div>
                  <div className="eyebrow">Max risk</div>
                </div>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className="rounded border border-[var(--border)] p-3">
                  <div className="eyebrow">Stated intent</div>
                  <p className="mt-2 text-sm">
                    {detail.data.session.user_intent}
                  </p>
                </div>
                <div className="rounded border border-red-200 bg-red-50 p-3">
                  <div className="eyebrow text-red-700">Final action</div>
                  <p className="mt-2 mono text-sm">
                    {detail.data.steps.at(-1)?.tool_name}
                  </p>
                </div>
              </div>
            </section>

            <section className="panel min-h-0 p-5">
              <h3 className="eyebrow text-[var(--ink)]">Risk Trajectory</h3>
              <Chart
                option={chartOption}
                style={{ height: "calc(100% - 22px)", minHeight: 260 }}
              />
            </section>

            <section className="panel p-5">
              <h3 className="eyebrow text-[var(--ink)]">
                Similar Precedents
              </h3>
              <div className="mt-3 grid gap-2">
                {detail.data.precedents.map((precedent) => (
                  <div
                    className="flex items-center justify-between rounded border border-[var(--border)] px-3 py-2"
                    key={precedent.trace_id}
                  >
                    <div>
                      <div className="text-sm font-semibold">
                        {precedent.tool_name}
                      </div>
                      <div className="mt-1 text-xs text-[var(--ink-muted)]">
                        {precedent.scenario_id}
                      </div>
                    </div>
                    <StatusBadge value={precedent.decision} />
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}

function TimelineCard({
  icon,
  title,
  body,
  decision,
  risk,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  decision?: string;
  risk?: number;
}) {
  return (
    <div className="relative mb-5">
      <div className="absolute -left-[49px] flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border)] bg-white">
        {icon}
      </div>
      <div
        className={`rounded border p-4 ${
          decision === "block"
            ? "border-red-300 bg-red-50"
            : "border-[var(--border)]"
        }`}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="text-sm font-semibold">{title}</div>
          {decision && <StatusBadge value={decision} />}
        </div>
        <p className="mt-2 mono text-xs leading-5 text-[var(--ink-muted)]">
          {body}
        </p>
        {risk !== undefined && (
          <div className="mt-3 h-1.5 overflow-hidden rounded bg-[var(--surface-highest)]">
            <div
              className={decision === "block" ? "h-full bg-red-600" : "h-full bg-emerald-600"}
              style={{ width: `${Math.max(3, risk * 100)}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
