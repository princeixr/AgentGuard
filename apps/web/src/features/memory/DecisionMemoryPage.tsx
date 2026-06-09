import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Search, SlidersHorizontal, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../../api/client";
import type { MemoryItem } from "../../api/types";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

const columnHelper = createColumnHelper<MemoryItem>();

export function DecisionMemoryPage() {
  const { agentId = "" } = useParams();
  const [query, setQuery] = useState("");
  const [decision, setDecision] = useState("");
  const [tool, setTool] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const params = useMemo(() => {
    const value = new URLSearchParams({ page_size: "100" });
    if (query.trim()) value.set("query", query.trim());
    if (decision) value.set("decision", decision);
    if (tool) value.set("tool", tool);
    return value;
  }, [decision, query, tool]);

  const memory = useQuery({
    queryKey: ["memory", agentId, params.toString()],
    queryFn: () => api.memory(agentId, params),
  });
  const detail = useQuery({
    queryKey: ["memory-detail", agentId, selected],
    queryFn: () => api.memoryDetail(agentId, selected!),
    enabled: Boolean(selected),
  });

  const tools = useMemo(
    () =>
      Array.from(new Set(memory.data?.items.map((item) => item.tool_name))).sort(),
    [memory.data],
  );
  const columns = useMemo(
    () => [
      columnHelper.accessor("timestamp", {
        header: "Timestamp",
        cell: ({ getValue }) => (
          <span className="mono text-[11px]">
            {new Date(getValue()).toLocaleString()}
          </span>
        ),
      }),
      columnHelper.accessor("agent_id", {
        header: "Agent",
        cell: ({ getValue }) => (
          <span className="mono text-xs">{getValue()}</span>
        ),
      }),
      columnHelper.accessor("tool_name", {
        header: "Tool",
        cell: ({ getValue }) => (
          <span className="mono text-xs font-semibold">{getValue()}</span>
        ),
      }),
      columnHelper.accessor("risk_score", {
        header: "Decision score",
        cell: ({ getValue }) => {
          const score = getValue();
          return (
            <span
              className={`inline-flex min-w-12 justify-center rounded px-2 py-1 mono text-xs font-semibold ${
                score >= 0.5
                  ? "bg-red-100 text-red-700"
                  : score >= 0.3
                    ? "bg-amber-100 text-amber-700"
                    : "bg-blue-50 text-blue-700"
              }`}
            >
              {score.toFixed(2)}
            </span>
          );
        },
      }),
      columnHelper.accessor("labels", {
        header: "Signals",
        cell: ({ getValue }) => (
          <div className="flex max-w-[330px] flex-wrap gap-1">
            {getValue()
              .slice(0, 3)
              .map((label) => (
                <span
                  className="rounded border border-[var(--border)] px-2 py-1 mono text-[9px]"
                  key={label}
                >
                  {label.replaceAll("_", " ")}
                </span>
              ))}
          </div>
        ),
      }),
      columnHelper.accessor("decision", {
        header: "Decision",
        cell: ({ getValue }) => <StatusBadge value={getValue()} />,
      }),
      columnHelper.accessor("guard_evaluation", {
        header: "Decision owner",
        cell: ({ getValue }) => {
          const guard = getValue();
          return guard ? (
            <div>
              <code className="text-[10px] font-semibold">{guard.enforced_by}</code>
              <div className="mt-1 text-[9px] uppercase tracking-wider text-[var(--ink-muted)]">
                {guard.firewall_mode} · {guard.enforcement_status}
              </div>
            </div>
          ) : (
            <span className="text-[10px] text-[var(--ink-muted)]">
              Historical trace
            </span>
          );
        },
      }),
    ],
    [],
  );
  const table = useReactTable({
    data: memory.data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (memory.isLoading) return <LoadingState label="Loading decision memory" />;
  if (memory.error) return <ErrorState message="Unable to query decision memory." />;

  return (
    <Dialog.Root open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
      <div className="flex h-full min-h-[650px] flex-col gap-4">
        <section className="panel flex items-center gap-3 p-3">
          <div className="relative min-w-[320px] flex-1">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]"
            />
            <input
              className="w-full rounded border border-[var(--border)] bg-[var(--surface-low)] py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
              placeholder="Search trace ID, agent, tool, signal, or explanation..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <SlidersHorizontal size={17} />
          <select
            className="rounded border border-[var(--border)] bg-white px-3 py-2 text-sm"
            value={tool}
            onChange={(event) => setTool(event.target.value)}
          >
            <option value="">Tool: All</option>
            {tools.map((item) => (
              <option value={item} key={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            className="rounded border border-[var(--border)] bg-white px-3 py-2 text-sm"
            value={decision}
            onChange={(event) => setDecision(event.target.value)}
          >
            <option value="">Decision: All</option>
            <option value="allow">Allow</option>
            <option value="warn">Warn</option>
            <option value="review">Review</option>
            <option value="require_approval">Require approval</option>
            <option value="block">Block</option>
          </select>
          <button
            className="px-2 py-2 text-xs font-semibold text-blue-700"
            onClick={() => {
              setQuery("");
              setDecision("");
              setTool("");
            }}
          >
            Clear filters
          </button>
        </section>

        <section className="panel min-h-0 flex-1 overflow-hidden">
          <div className="flex h-12 items-center justify-between border-b border-[var(--border)] px-4">
            <span className="eyebrow text-[var(--ink)]">Governance Records</span>
            <span className="text-xs text-[var(--ink-muted)]">
              {memory.data?.total ?? 0} records found
            </span>
          </div>
          <div className="h-[calc(100%-48px)] overflow-auto subtle-scrollbar">
            <table className="w-full border-collapse text-left">
              <thead className="sticky top-0 z-10 bg-[var(--surface-container)]">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th
                        className="border-b border-[var(--border)] px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--ink-muted)]"
                        key={header.id}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <Dialog.Trigger asChild key={row.id}>
                    <tr
                      className="cursor-pointer border-b border-[var(--border)] hover:bg-[var(--surface-low)]"
                      onClick={() => setSelected(row.original.trace_id)}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td className="px-4 py-3.5" key={cell.id}>
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </td>
                      ))}
                    </tr>
                  </Dialog.Trigger>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/15" />
        <Dialog.Content className="fixed bottom-0 right-0 top-0 z-50 w-[520px] overflow-auto border-l border-[var(--border)] bg-white p-0 shadow-xl subtle-scrollbar">
          <div className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-[var(--border)] bg-white px-5">
            <div>
              <Dialog.Title className="text-base font-bold">
                Trace Details
              </Dialog.Title>
              <Dialog.Description className="mt-1 mono text-[10px] text-[var(--ink-muted)]">
                {selected}
              </Dialog.Description>
            </div>
            <Dialog.Close className="rounded p-2 hover:bg-[var(--surface-high)]">
              <X size={18} />
            </Dialog.Close>
          </div>
          {detail.isLoading ? (
            <div className="p-5">
              <LoadingState />
            </div>
          ) : detail.error || !detail.data ? (
            <div className="p-5">
              <ErrorState message="Unable to load trace details." />
            </div>
          ) : (
            <div className="space-y-5 p-5">
              <div className="flex items-center justify-between">
                <code className="text-lg font-bold">
                  {detail.data.item.tool_name}
                </code>
                <StatusBadge value={detail.data.item.decision} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Metric
                  label="Decision score"
                  value={detail.data.item.risk_score.toFixed(2)}
                />
                <Metric
                  label="Latency"
                  value={`${detail.data.decision.latency_ms}ms`}
                />
              </div>
              <DetailSection title="Intent">
                {detail.data.trace.intent.normalized_intent}
              </DetailSection>
              <DetailSection title="Arguments">
                <pre className="whitespace-pre-wrap mono text-[11px]">
                  {JSON.stringify(
                    detail.data.trace.proposed_tool_call.arguments,
                    null,
                    2,
                  )}
                </pre>
              </DetailSection>
              <DetailSection title="Decision explanation">
                {detail.data.item.explanation}
              </DetailSection>
              {detail.data.item.guard_evaluation && (
                <>
                  <DetailSection title="FirewallV2 decision">
                    <div className="grid grid-cols-2 gap-2">
                      <Metric
                        label="Enforced by"
                        value={detail.data.item.guard_evaluation.enforced_by}
                      />
                      <Metric
                        label="Policy"
                        value={`${detail.data.item.guard_evaluation.policy_id ?? "unknown"}@${detail.data.item.guard_evaluation.policy_version ?? "unknown"}`}
                      />
                    </div>
                  </DetailSection>
                  <DetailSection title="Matched policy rules">
                    <div className="flex flex-wrap gap-2">
                      {detail.data.item.guard_evaluation.matched_rules.length ? (
                        detail.data.item.guard_evaluation.matched_rules.map((rule) => (
                          <code
                            className="rounded bg-blue-50 px-2 py-1 text-[10px] text-blue-800"
                            key={rule.rule_id}
                          >
                            {rule.rule_id}: {rule.effect}
                          </code>
                        ))
                      ) : (
                        <span className="text-[var(--ink-muted)]">
                          Policy default applied.
                        </span>
                      )}
                    </div>
                  </DetailSection>
                  <DetailSection title="Normalized action">
                    <pre className="whitespace-pre-wrap mono text-[11px]">
                      {JSON.stringify(
                        detail.data.item.guard_evaluation.normalized_action,
                        null,
                        2,
                      )}
                    </pre>
                  </DetailSection>
                  <DetailSection title="Tier results">
                    <div className="space-y-2">
                      {detail.data.item.guard_evaluation.tier_results.map((tier) => (
                        <div
                          className="rounded border border-[var(--border)] p-3"
                          key={String(tier.tier_result_id ?? tier.tier)}
                        >
                          <div className="flex items-center justify-between">
                            <code className="text-xs font-semibold">
                              {String(tier.tier)}
                            </code>
                            <StatusBadge value={String(tier.recommendation)} />
                          </div>
                          <p className="mt-2 text-xs text-[var(--ink-muted)]">
                            {String(tier.explanation)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </DetailSection>
                </>
              )}
              <DetailSection title="Dominant signals">
                <div className="flex flex-wrap gap-2">
                  {detail.data.score.dominant_signals.map((signal: string) => (
                    <span
                      className="rounded border border-[var(--border)] px-2 py-1 mono text-[10px]"
                      key={signal}
                    >
                      {signal}
                    </span>
                  ))}
                </div>
              </DetailSection>
              <DetailSection title="Precedents">
                <div className="space-y-2">
                  {detail.data.precedents.map((precedent) => (
                    <div
                      className="flex items-center justify-between rounded border border-[var(--border)] p-3"
                      key={precedent.trace_id}
                    >
                      <code className="text-xs">{precedent.tool_name}</code>
                      <StatusBadge value={precedent.decision} />
                    </div>
                  ))}
                </div>
              </DetailSection>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface-low)] p-3">
      <div className="eyebrow">{label}</div>
      <div className="mt-2 text-xl font-bold">{value}</div>
    </div>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="eyebrow">{title}</h3>
      <div className="mt-2 text-sm leading-6">{children}</div>
    </section>
  );
}
