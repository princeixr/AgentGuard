import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Braces,
  CheckCircle2,
  FileLock2,
  GitBranch,
  LockKeyhole,
  Save,
  Settings2,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../../api/client";
import type { GuardAdminComponent } from "../../api/types";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { DEMO_AGENT_ID } from "../../config/demo";

const FLOW_IDS = [
  "interception",
  "tool_descriptors",
  "policy_engine",
  "normalization",
  "intent_contract",
  "tier_1",
  "tier_2",
  "tier_3",
  "firewall_v1",
];

export function GuardAdminPage() {
  const { agentId = DEMO_AGENT_ID } = useParams();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [editorMessage, setEditorMessage] = useState("");
  const [editorError, setEditorError] = useState("");
  const guard = useQuery({
    queryKey: ["guard-admin", agentId],
    queryFn: () => api.guardAdmin(agentId),
  });
  const policy = useQuery({
    queryKey: ["agent-policy", agentId],
    queryFn: () => api.agentPolicy(agentId),
  });
  const savePolicy = useMutation({
    mutationFn: ({
      expectedHash,
      document,
    }: {
      expectedHash: string;
      document: Record<string, unknown>;
    }) => api.updateAgentPolicy(agentId, expectedHash, document),
    onSuccess: async (updated) => {
      queryClient.setQueryData(["agent-policy", agentId], updated);
      setDraft(JSON.stringify(updated.document, null, 2));
      setEditorError("");
      setEditorMessage(
        `Published ${updated.policy_id}@${updated.version}. New V2 interceptions will use this policy.`,
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["guard-admin", agentId] }),
        queryClient.invalidateQueries({ queryKey: ["agent-definition", agentId] }),
      ]);
    },
    onError: (error) => {
      setEditorMessage("");
      setEditorError(error instanceof Error ? error.message : "Policy save failed.");
    },
  });

  if (guard.isLoading || policy.isLoading) {
    return <LoadingState label="Loading Guard Admin" />;
  }
  if (guard.isError || policy.isError || !guard.data || !policy.data) {
    return <ErrorState message="Unable to load the AgentGuard configuration." />;
  }

  const data = guard.data;
  const policyData = policy.data;
  const flow = FLOW_IDS.map((id) =>
    data.components.find((component) => component.component_id === id),
  ).filter((component): component is GuardAdminComponent => Boolean(component));
  const remaining = data.components.filter(
    (component) => !FLOW_IDS.includes(component.component_id),
  );
  const openEditor = () => {
    setDraft(JSON.stringify(policyData.document, null, 2));
    setEditorMessage("");
    setEditorError("");
    setEditorOpen(true);
  };
  const parseDraft = (): Record<string, unknown> | null => {
    try {
      const parsed = JSON.parse(draft);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("The policy must be a JSON object.");
      }
      setEditorError("");
      return parsed as Record<string, unknown>;
    } catch (error) {
      setEditorMessage("");
      setEditorError(
        error instanceof Error ? error.message : "The policy is not valid JSON.",
      );
      return null;
    }
  };
  const validateDraft = async () => {
    const document = parseDraft();
    if (!document) return;
    try {
      const result = await api.validateAgentPolicy(agentId, document);
      if (!result.valid) {
        setEditorMessage("");
        setEditorError(result.errors.join("\n"));
        return;
      }
      setEditorError("");
      setEditorMessage(
        "Policy is valid. Saving will publish it as the next patch version.",
      );
    } catch (error) {
      setEditorMessage("");
      setEditorError(
        error instanceof Error ? error.message : "Policy validation failed.",
      );
    }
  };
  const publishDraft = () => {
    const document = parseDraft();
    if (!document) return;
    savePolicy.mutate({
      expectedHash: policyData.effective_hash,
      document,
    });
  };

  return (
    <div className="space-y-4">
      {data.warnings.map((warning) => (
        <div
          className="flex items-start gap-3 rounded border border-amber-300 bg-[var(--amber-bg)] px-4 py-3 text-sm"
          key={warning}
        >
          <AlertTriangle className="mt-0.5 shrink-0 text-[var(--amber)]" size={18} />
          <span>{warning}</span>
        </div>
      ))}

      <section className="panel p-5">
        <div className="flex items-start justify-between gap-8">
          <div>
            <div className="eyebrow">AgentGuard control plane</div>
            <h2 className="mt-2 text-2xl font-bold">Firewall architecture</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
              This page reports the actual implementation state for the selected
              agent. Policy edits are validated and published to the V2 backend;
              unfinished controls remain read-only.
            </p>
          </div>
          <div className="grid min-w-[430px] grid-cols-3 divide-x divide-[var(--border)] rounded border border-[var(--border)] bg-[var(--surface-low)]">
            <Fact label="Mode" value={data.firewall_mode} />
            <Fact label="Enforced by" value={data.active_enforcement} />
            <Fact
              label="Force block"
              value={data.force_block_enabled ? "enabled" : "disabled"}
            />
          </div>
        </div>
      </section>

      <section className="panel p-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="eyebrow">Request evaluation flow</div>
            <h3 className="mt-2 text-lg font-bold">Intercepted tool call</h3>
          </div>
          <div className="text-xs text-[var(--ink-muted)]">
            {data.architecture_version}
          </div>
        </div>
        <div className="mt-5 grid grid-cols-3 gap-3">
          {flow.map((component, index) => (
            <div className="relative" key={component.component_id}>
              <ComponentCard component={component} />
              {index < flow.length - 1 && index % 3 !== 2 && (
                <ArrowRight
                  className="absolute -right-[14px] top-1/2 z-10 -translate-y-1/2 rounded-full bg-white text-[var(--ink-muted)]"
                  size={26}
                />
              )}
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-[1.05fr_1.4fr] gap-4">
        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="eyebrow">Central guardrail</div>
              <h3 className="mt-2 text-lg font-bold">Policy</h3>
            </div>
            <StatusBadge value={data.policy.status} />
          </div>
          <div className="mt-5 rounded border border-[var(--border)] bg-[var(--surface-low)] p-4">
            <div className="flex items-center gap-3">
              <FileLock2 size={20} />
              <code className="font-semibold">{data.policy.policy_id}</code>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
              <Fact
                label="Source"
                value={data.policy.source.split("/").pop() ?? data.policy.source}
                compact
              />
              <Fact
                label="Version"
                value={data.policy.version ?? "unknown"}
                compact
              />
            </div>
            <div className="mt-3 border-t border-[var(--border)] pt-3">
              <div className="eyebrow">Effective hash</div>
              <code className="mt-1 block break-all text-[10px]">
                {data.policy.effective_hash}
              </code>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-[var(--ink-muted)]">
            {data.policy.explanation}
          </p>
          <div className="mt-5 rounded border border-[var(--border)] bg-white px-4 py-3 text-xs leading-5 text-[var(--ink-muted)]">
            Policy configuration and publishing controls are available in the
            complete policy section below.
          </div>
        </section>

        <section className="panel p-5">
          <div>
            <div className="eyebrow">Agent integration</div>
            <h3 className="mt-2 text-lg font-bold">Tool capability registry</h3>
          </div>
          <div className="mt-5 space-y-3">
            {data.tools.map((tool) => (
              <div
                className="rounded border border-[var(--border)] p-4"
                key={tool.name}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 font-mono text-sm font-semibold">
                      <Wrench size={15} />
                      {tool.name}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {tool.capabilities.map((capability) => (
                        <code
                          className="rounded bg-[var(--surface-low)] px-2 py-1 text-[10px]"
                          key={capability}
                        >
                          {capability}
                        </code>
                      ))}
                    </div>
                  </div>
                  <StatusBadge value={tool.metadata_status} />
                </div>
                <div className="mt-3 grid grid-cols-3 text-xs text-[var(--ink-muted)]">
                  <span>Impact: {tool.impact}</span>
                  <span>Normalizer: {tool.normalizer}</span>
                  <span>Provider: {tool.provider}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel p-5">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="eyebrow">Published policy</div>
            <h3 className="mt-2 text-lg font-bold">{policyData.document.name}</h3>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--ink-muted)]">
              {policyData.document.description}
            </p>
          </div>
          <div className="flex items-start gap-3">
            <div className="text-right">
              <StatusBadge value={policyData.validation} />
              <div className="mt-2 font-mono text-xs">
                {policyData.policy_id}@{policyData.version}
              </div>
            </div>
            <button
              className="flex items-center gap-2 rounded bg-black px-4 py-2 text-sm font-semibold text-white"
              onClick={editorOpen ? () => setEditorOpen(false) : openEditor}
              type="button"
            >
              <Settings2 size={16} />
              {editorOpen ? "Close editor" : "Edit policy"}
            </button>
          </div>
        </div>

        {editorOpen && (
          <div className="mt-5 rounded border border-blue-300 bg-blue-50/40 p-4">
            <div className="flex items-start justify-between gap-6">
              <div>
                <div className="eyebrow">Policy JSON editor</div>
                <p className="mt-2 max-w-4xl text-xs leading-5 text-[var(--ink-muted)]">
                  The backend validates the complete document and publishes it
                  atomically as the next patch version. Policy ID and scope cannot be
                  changed.
                </p>
              </div>
              <StatusBadge value="editable" />
            </div>
            <div className="mt-3 rounded border border-amber-300 bg-[var(--amber-bg)] px-4 py-3 text-xs leading-5">
              Changes affect FirewallV2 recommendations on the next interception.
              FirewallV1 still controls execution in <code>v2_shadow</code>.
            </div>
            <textarea
              aria-label="Policy JSON"
              className="mt-4 min-h-[520px] w-full resize-y rounded border border-[var(--border)] bg-[#111827] p-4 font-mono text-xs leading-5 text-[#e5e7eb] outline-none focus:border-blue-500"
              onChange={(event) => {
                setDraft(event.target.value);
                setEditorMessage("");
                setEditorError("");
              }}
              spellCheck={false}
              value={draft}
            />
            {editorError && (
              <pre className="mt-3 whitespace-pre-wrap rounded border border-red-300 bg-red-50 px-4 py-3 text-xs text-red-800">
                {editorError}
              </pre>
            )}
            {editorMessage && (
              <div className="mt-3 rounded border border-emerald-300 bg-emerald-50 px-4 py-3 text-xs text-emerald-800">
                {editorMessage}
              </div>
            )}
            <div className="mt-4 flex justify-end gap-3">
              <button
                className="rounded border border-[var(--border)] bg-white px-4 py-2 text-sm font-semibold"
                onClick={validateDraft}
                type="button"
              >
                Validate
              </button>
              <button
                className="flex items-center gap-2 rounded bg-black px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                disabled={savePolicy.isPending}
                onClick={publishDraft}
                type="button"
              >
                <Save size={16} />
                {savePolicy.isPending ? "Publishing..." : "Save and publish"}
              </button>
            </div>
          </div>
        )}

        <div className="mt-5 grid grid-cols-4 gap-3">
          <PolicyTile
            label="Schema"
            value={policyData.document.schema_version}
          />
          <PolicyTile label="Status" value={policyData.document.status} />
          <PolicyTile
            label="Workspace"
            value={policyData.document.scope.workspace_id}
          />
          <PolicyTile
            label="Deployment"
            value={policyData.document.scope.deployment_id ?? "all deployments"}
          />
        </div>

        <PolicySection title="Default decisions">
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(policyData.document.defaults).map(([name, value]) => (
              <div
                className="rounded border border-[var(--border)] bg-[var(--surface-low)] p-3"
                key={name}
              >
                <code className="text-xs font-semibold">{name}</code>
                <div className="mt-3">
                  <StatusBadge value={value} />
                </div>
              </div>
            ))}
          </div>
        </PolicySection>

        <PolicySection title="Tier routing">
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(policyData.document.routing).map(([route, tiers]) => (
              <div
                className="rounded border border-[var(--border)] bg-white p-4"
                key={route}
              >
                <code className="text-sm font-semibold">{route}</code>
                <div className="mt-3 flex flex-wrap gap-2">
                  {tiers.map((tier) => (
                    <span
                      className="rounded bg-blue-50 px-2 py-1 font-mono text-[11px] text-blue-800"
                      key={tier}
                    >
                      {tier}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </PolicySection>

        <PolicySection title={`Rules (${policyData.document.rules.length})`}>
          <div className="grid grid-cols-2 gap-3">
            {policyData.document.rules.map((rule) => (
              <article
                className="rounded border border-[var(--border)] bg-white p-4"
                key={rule.rule_id}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <code className="break-words text-sm font-bold">
                      {rule.rule_id}
                    </code>
                    <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
                      {rule.description}
                    </p>
                  </div>
                  <StatusBadge value={rule.effect} />
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[var(--border)] pt-3">
                  <RuleFact label="Severity" value={rule.severity} />
                  <RuleFact
                    label="Override"
                    value={rule.non_overridable ? "not allowed" : "allowed"}
                  />
                </div>
                <RuleValues
                  label="Capabilities"
                  values={rule.match.capabilities_any}
                  emptyLabel="Any capability"
                />
                <RuleValues
                  label="Tools"
                  values={rule.match.tools_any}
                  emptyLabel="Any tool"
                />
                <ResourceConstraints
                  constraints={rule.match.resource_constraints}
                />
              </article>
            ))}
          </div>
        </PolicySection>

        <PolicySection title="Policy notes">
          <div className="grid grid-cols-2 gap-3">
            {policyData.document.notes.map((note, index) => (
              <div
                className="rounded border border-[var(--border)] bg-[var(--surface-low)] p-4 text-xs leading-5"
                key={`${index}-${note}`}
              >
                {note}
              </div>
            ))}
          </div>
        </PolicySection>
      </section>

      <section className="panel p-5">
        <div className="eyebrow">Supporting controls</div>
        <div className="mt-4 grid grid-cols-2 gap-3">
          {remaining.map((component) => (
            <ComponentCard component={component} key={component.component_id} />
          ))}
        </div>
      </section>
    </div>
  );
}

function PolicySection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-6 border-t border-[var(--border)] pt-5">
      <div className="eyebrow mb-3">{title}</div>
      {children}
    </div>
  );
}

function PolicyTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface-low)] p-4">
      <div className="eyebrow">{label}</div>
      <code className="mt-2 block break-words text-xs font-semibold">{value}</code>
    </div>
  );
}

function RuleFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className="mt-1 text-xs font-semibold">{value}</div>
    </div>
  );
}

function RuleValues({
  label,
  values,
  emptyLabel,
}: {
  label: string;
  values: string[];
  emptyLabel: string;
}) {
  return (
    <div className="mt-4">
      <div className="eyebrow">{label}</div>
      {values.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {values.map((value) => (
            <code
              className="rounded bg-[var(--surface-low)] px-2 py-1 text-[10px]"
              key={value}
            >
              {value}
            </code>
          ))}
        </div>
      ) : (
        <div className="mt-2 text-xs text-[var(--ink-muted)]">{emptyLabel}</div>
      )}
    </div>
  );
}

function ResourceConstraints({
  constraints,
}: {
  constraints: Record<string, unknown>;
}) {
  const entries = Object.entries(constraints);
  return (
    <div className="mt-4">
      <div className="eyebrow">Resource constraints</div>
      {entries.length > 0 ? (
        <div className="mt-2 space-y-2">
          {entries.map(([name, value]) => (
            <div
              className="rounded bg-[var(--surface-low)] px-3 py-2"
              key={name}
            >
              <code className="text-[10px] font-bold">{name}</code>
              <code className="mt-1 block break-words text-[10px] text-[var(--ink-muted)]">
                {JSON.stringify(value)}
              </code>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-2 text-xs text-[var(--ink-muted)]">No restriction</div>
      )}
    </div>
  );
}

function ComponentCard({ component }: { component: GuardAdminComponent }) {
  const Icon =
    component.status === "operational"
      ? CheckCircle2
      : component.component_id.includes("tier")
        ? GitBranch
        : component.component_id.includes("policy")
          ? LockKeyhole
          : component.component_id.includes("descriptor")
            ? Braces
            : ShieldCheck;
  return (
    <div className="h-full rounded border border-[var(--border)] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon size={17} />
          <span className="text-sm font-semibold">{component.name}</span>
        </div>
        <StatusBadge value={component.status.replace("_", " ")} />
      </div>
      <div className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--ink-muted)]">
        {component.layer}
      </div>
      <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
        {component.summary}
      </p>
      <div className="mt-3 border-t border-[var(--border)] pt-3 text-[11px] leading-4">
        {component.management}
      </div>
    </div>
  );
}

function Fact({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: string;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "" : "px-4 py-3"}>
      <div className="eyebrow">{label}</div>
      <div className="mt-1 font-mono text-xs font-semibold">{value}</div>
    </div>
  );
}
