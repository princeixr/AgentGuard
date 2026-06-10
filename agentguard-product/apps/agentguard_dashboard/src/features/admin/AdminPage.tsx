import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History, Lock, Save, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AgentPolicy } from "../../api/types";
import { useProductionAgent } from "../../api/useProductionAgent";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";

export function AdminPage() {
  const queryClient = useQueryClient();
  const { agent, agentId, agents } = useProductionAgent();
  const policy = useQuery({
    queryKey: ["agent-policy", agentId],
    queryFn: () => api.agentPolicy(agentId),
    enabled: Boolean(agentId),
  });
  const guard = useQuery({
    queryKey: ["guard-admin", agentId],
    queryFn: () => api.guardAdmin(agentId),
    enabled: Boolean(agentId),
  });
  const [draft, setDraft] = useState<AgentPolicy["document"] | null>(null);
  const [validationMessage, setValidationMessage] = useState("");

  useEffect(() => {
    if (policy.data) setDraft(structuredClone(policy.data.document));
  }, [policy.data]);

  const save = useMutation({
    mutationFn: async () => {
      if (!draft || !policy.data) throw new Error("Policy is not loaded.");
      const validation = await api.validateAgentPolicy(agentId, draft);
      if (!validation.valid) {
        throw new Error(validation.errors.join("\n") || "Policy validation failed.");
      }
      return api.updateAgentPolicy(agentId, policy.data.effective_hash, draft);
    },
    onSuccess: (next) => {
      setValidationMessage(`Published ${next.policy_id}@${next.version}`);
      queryClient.setQueryData(["agent-policy", agentId], next);
      void queryClient.invalidateQueries({ queryKey: ["guard-admin", agentId] });
    },
    onError: (error) =>
      setValidationMessage(error instanceof Error ? error.message : "Policy update failed."),
  });

  if (agents.isLoading || policy.isLoading || guard.isLoading) {
    return <LoadingState label="Loading policy administration" />;
  }
  if (agents.error || policy.error || guard.error) {
    return <ErrorState message="Unable to load policy administration." />;
  }
  if (!agent || !draft || !policy.data || !guard.data) {
    return (
      <div className="card">
        <EmptyState title="No connected agent" message="An agent is required to manage policy." />
      </div>
    );
  }

  return (
    <div className="admin-layout">
      <aside className="admin-tabs">
        <h3 className="eyebrow">Administration</h3>
        <span className="admin-tab admin-tab-active">Policy Overview</span>
        <span className="admin-tab">Tool Permissions</span>
        <span className="admin-tab">Approval Rules</span>
        <span className="admin-tab">Tier Configuration</span>
        <span className="admin-tab">Audit Settings</span>
      </aside>

      <div className="admin-canvas">
        <header className="admin-header">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h2 style={{ margin: 0, fontSize: 24 }}>
                {draft.name} <span className="mono">v{draft.version}</span>
              </h2>
              <StatusChip value={draft.status} label={draft.status} />
            </div>
            <div className="meta-line">
              <span>{policy.data.effective_hash.slice(0, 20)}…</span>
              <span>{agent.name}</span>
              <span>{guard.data.active_enforcement}</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="button"
              onClick={() => {
                setDraft(structuredClone(policy.data.document));
                setValidationMessage("");
              }}
              type="button"
            >
              <History size={15} /> Revert
            </button>
            <button
              className="button button-primary"
              disabled={save.isPending}
              onClick={() => save.mutate()}
              type="button"
            >
              <Save size={15} /> {save.isPending ? "Validating…" : "Save Changes"}
            </button>
          </div>
        </header>

        <div className="admin-content">
          {validationMessage && <div className="alert">{validationMessage}</div>}
          {guard.data.warnings.map((warning) => (
            <div className="alert" key={warning}>{warning}</div>
          ))}

          <section className="card">
            <div className="policy-section-header">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <ShieldCheck size={18} color="var(--text-secondary)" />
                <strong>Platform Baseline</strong>
              </div>
              <span className="tag"><Lock size={11} /> Locked</span>
            </div>
            <div className="policy-section-body" style={{ color: "var(--text-secondary)", fontSize: 13 }}>
              Deterministic policy blocks and approval requirements are non-overridable.
              Unknown tools use <code>{draft.defaults.unmatched_tool}</code>; parser failures
              use <code>{draft.defaults.parser_failure}</code>.
            </div>
          </section>

          <section className="card">
            <div className="policy-section-header">
              <strong>Workspace Policy</strong>
              <span className="mono" style={{ color: "var(--text-muted)", fontSize: 10 }}>
                {draft.scope.workspace_id}
              </span>
            </div>
            <div className="policy-section-body">
              <label className="eyebrow" htmlFor="policy-description">Description</label>
              <textarea
                className="textarea"
                id="policy-description"
                onChange={(event) =>
                  setDraft({ ...draft, description: event.target.value })
                }
                rows={3}
                style={{ marginTop: 8, resize: "vertical" }}
                value={draft.description}
              />
            </div>
          </section>

          <section className="card">
            <div className="policy-section-header">
              <div>
                <strong>Agent Policy: {agent.name}</strong>
                <div className="mono" style={{ marginTop: 4, color: "var(--text-muted)", fontSize: 10 }}>
                  agent_id: {agent.agent_id}
                </div>
              </div>
              <span className="tag">{draft.rules.length} rules</span>
            </div>
            <div>
              {draft.rules.map((rule, index) => (
                <div className="policy-rule" key={rule.rule_id}>
                  <div>
                    <div style={{ color: "white", fontWeight: 600 }}>{rule.rule_id}</div>
                    <div
                      style={{
                        marginTop: 5,
                        color: "var(--text-secondary)",
                        fontSize: 12,
                        lineHeight: 1.45,
                      }}
                    >
                      {rule.description}
                    </div>
                  </div>
                  <div className="tag-list">
                    {rule.match.capabilities_any.map((capability) => (
                      <span className="tag" key={capability}>{capability}</span>
                    ))}
                    {rule.match.tools_any.map((tool) => (
                      <span className="tag" key={tool}>{tool}</span>
                    ))}
                  </div>
                  <select
                    className="select"
                    onChange={(event) => {
                      const rules = draft.rules.map((item, ruleIndex) =>
                        ruleIndex === index
                          ? {
                              ...item,
                              effect: event.target.value as
                                | "allow"
                                | "require_approval"
                                | "block",
                            }
                          : item,
                      );
                      setDraft({ ...draft, rules });
                    }}
                    value={rule.effect}
                  >
                    <option value="allow">ALLOW</option>
                    <option value="require_approval">REQ APPROVAL</option>
                    <option value="block">BLOCK</option>
                  </select>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="policy-section-header">
              <strong>Runtime Components</strong>
              <span className="tag">{guard.data.firewall_mode}</span>
            </div>
            <div>
              {guard.data.components.map((component) => (
                <div className="policy-rule" key={component.component_id}>
                  <div>
                    <div style={{ color: "white", fontWeight: 600 }}>{component.name}</div>
                    <div className="eyebrow" style={{ marginTop: 5 }}>{component.layer}</div>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.45 }}>
                    {component.summary}
                  </div>
                  <StatusChip value={component.status} label={component.status} />
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
