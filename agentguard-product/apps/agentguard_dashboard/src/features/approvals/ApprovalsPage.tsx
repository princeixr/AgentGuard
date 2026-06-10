import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ShieldAlert, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import type { PendingApproval } from "../../api/types";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [noteById, setNoteById] = useState<Record<string, string>>({});
  const approvals = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => api.approvals("pending"),
    refetchInterval: 2_000,
  });
  const resolve = useMutation({
    mutationFn: ({
      approval,
      action,
    }: {
      approval: PendingApproval;
      action: "approve" | "reject";
    }) =>
      action === "approve"
        ? api.approve(approval.approval_id, noteById[approval.approval_id])
        : api.reject(approval.approval_id, noteById[approval.approval_id]),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
    },
  });

  useEffect(() => {
    const source = new EventSource("/api/v1/events/stream");
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
    };
    source.addEventListener("approval.pending", refresh);
    source.addEventListener("approval.resolved", refresh);
    return () => source.close();
  }, [queryClient]);

  if (approvals.isLoading) {
    return <LoadingState label="Loading approval queue" />;
  }
  if (approvals.error) {
    return <ErrorState message="Approval queue is unavailable." />;
  }

  const items = approvals.data?.items ?? [];
  return (
    <div className="space-y-5">
      <section className="panel flex items-center justify-between p-5">
        <div>
          <div className="eyebrow">Human approval queue</div>
          <h2 className="mt-1 text-2xl font-bold tracking-[-0.03em]">
            Pending Tool Calls
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-[var(--ink-muted)]">
            AgentGuard pauses calls that need approval. Approving lets the
            agent execute the original tool call; rejecting fails closed.
          </p>
        </div>
        <div className="rounded bg-[var(--surface-low)] px-4 py-3 text-center">
          <div className="text-3xl font-bold">{items.length}</div>
          <div className="eyebrow">pending</div>
        </div>
      </section>

      {items.length === 0 ? (
        <section className="panel flex min-h-[360px] flex-col items-center justify-center text-center">
          <ShieldAlert size={34} />
          <h3 className="mt-4 text-lg font-bold">No pending approvals</h3>
          <p className="mt-2 max-w-md text-sm text-[var(--ink-muted)]">
            When a connected agent proposes a sensitive tool call, it will show
            up here in real time.
          </p>
        </section>
      ) : (
        <div className="grid gap-4">
          {items.map((approval) => (
            <section className="panel p-5" key={approval.approval_id}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <code className="text-xl font-bold">{approval.tool_name}</code>
                    <StatusBadge value={approval.status} />
                  </div>
                  <p className="mt-2 max-w-4xl text-sm leading-6">
                    {approval.explanation}
                  </p>
                </div>
                <div className="mono text-right text-[11px] text-[var(--ink-muted)]">
                  <div>{approval.agent_id}</div>
                  <div>{approval.session_id}</div>
                  <div>{new Date(approval.created_at).toLocaleString()}</div>
                </div>
              </div>

              <div className="mt-5 grid grid-cols-3 gap-4">
                <div className="rounded border border-[var(--border)] p-4">
                  <div className="eyebrow">User intent</div>
                  <p className="mt-2 text-sm leading-5">{approval.user_request}</p>
                </div>
                <div className="rounded border border-[var(--border)] p-4">
                  <div className="eyebrow">Tool arguments</div>
                  <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap mono text-[11px] leading-5">
                    {JSON.stringify(approval.arguments, null, 2)}
                  </pre>
                </div>
                <div className="rounded border border-[var(--border)] p-4">
                  <div className="eyebrow">Combiner</div>
                  <div className="mt-2 flex items-center gap-2">
                    <StatusBadge
                      value={
                        approval.guard_evaluation?.recommendation ??
                        "require_approval"
                      }
                    />
                    <code className="text-[11px]">
                      {approval.guard_evaluation?.enforced_by ?? "firewall_v2"}
                    </code>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
                    {approval.guard_evaluation?.explanation}
                  </p>
                </div>
              </div>

              <div className="mt-5 rounded border border-blue-200 bg-blue-50/60 p-4">
                <div className="eyebrow text-blue-700">Tier evidence</div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {(approval.guard_evaluation?.tier_results ?? []).map((tier) => (
                    <div
                      className="rounded border border-blue-200 bg-white p-3"
                      key={String(tier.tier_result_id ?? tier.tier)}
                    >
                      <div className="flex items-center justify-between">
                        <code className="font-semibold">{String(tier.tier)}</code>
                        <StatusBadge value={String(tier.recommendation)} />
                      </div>
                      <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
                        {String(tier.explanation ?? "")}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 flex items-center gap-3">
                <input
                  className="min-w-0 flex-1 rounded border border-[var(--border)] px-3 py-2 text-sm"
                  onChange={(event) =>
                    setNoteById((current) => ({
                      ...current,
                      [approval.approval_id]: event.target.value,
                    }))
                  }
                  placeholder="Optional approval note"
                  value={noteById[approval.approval_id] ?? ""}
                />
                <button
                  className="flex items-center gap-2 rounded bg-black px-4 py-2 text-sm font-semibold text-white"
                  disabled={resolve.isPending}
                  onClick={() => resolve.mutate({ approval, action: "approve" })}
                  type="button"
                >
                  <Check size={16} /> Approve
                </button>
                <button
                  className="flex items-center gap-2 rounded bg-red-600 px-4 py-2 text-sm font-semibold text-white"
                  disabled={resolve.isPending}
                  onClick={() => resolve.mutate({ approval, action: "reject" })}
                  type="button"
                >
                  <X size={16} /> Reject
                </button>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
