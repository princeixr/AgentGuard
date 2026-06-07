import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bot,
  Braces,
  CheckCircle2,
  FlaskConical,
  KeyRound,
  Play,
  RadioTower,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function AgentDetailPage() {
  const { agentId = "" } = useParams();
  const [message, setMessage] = useState("");
  const agent = useQuery({
    queryKey: ["agent", agentId],
    queryFn: () => api.agent(agentId),
  });
  const definition = useQuery({
    queryKey: ["agent-definition", agentId],
    queryFn: () => api.agentDefinition(agentId),
  });
  const testRun = useMutation({
    mutationFn: () => api.runAgentTest(agentId, message.trim()),
  });

  if (agent.isLoading || definition.isLoading) {
    return <LoadingState label="Loading agent definition" />;
  }
  if (agent.error || definition.error || !agent.data || !definition.data) {
    return <ErrorState message="Unable to load the registered agent definition." />;
  }

  const config = definition.data;
  const deployment = agent.data.deployments[0];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <Link
          className="flex items-center gap-2 text-sm font-semibold text-[var(--ink-muted)]"
          to="/agents"
        >
          <ArrowLeft size={16} />
          All agents
        </Link>
        <Link
          className="rounded bg-[var(--blue)] px-4 py-2 text-xs font-semibold text-white"
          to={`/agents/${agentId}/live`}
        >
          Open live dashboard
        </Link>
      </div>

      <section className="panel p-5">
        <div className="flex items-start justify-between gap-6">
          <div className="flex gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded bg-black text-white">
              <Bot size={25} />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold">{agent.data.name}</h2>
                <StatusBadge value={agent.data.status} />
              </div>
              <p className="mt-2 max-w-3xl text-sm text-[var(--ink-muted)]">
                {config.description}
              </p>
              <code className="mt-3 block text-xs text-[var(--ink-muted)]">
                {agentId}
              </code>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-xs">
            <DefinitionFact label="Framework" value="Google ADK" />
            <DefinitionFact label="Model" value={config.model} />
            <DefinitionFact label="Environment" value={deployment?.environment} />
            <DefinitionFact label="Runtime" value={config.runtime_name} />
          </div>
        </div>
      </section>

      <div className="grid grid-cols-[minmax(0,1.15fr)_minmax(400px,0.85fr)] gap-5">
        <div className="space-y-5">
          <section className="panel overflow-hidden">
            <SectionHeader icon={<Braces size={17} />} title="System Instruction" />
            <pre className="whitespace-pre-wrap p-5 font-mono text-xs leading-6 text-[#343434]">
              {config.system_instruction}
            </pre>
          </section>

          <section className="panel overflow-hidden">
            <SectionHeader icon={<Wrench size={17} />} title="Tool Registry" />
            <div className="divide-y divide-[var(--border)]">
              {config.tools.map((tool) => (
                <div className="p-5" key={tool.name}>
                  <div className="flex items-start justify-between gap-5">
                    <div>
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-bold">{tool.name}</code>
                        <StatusBadge value={tool.enabled ? "enabled" : "disabled"} />
                      </div>
                      <p className="mt-2 text-sm text-[var(--ink-muted)]">
                        {tool.description}
                      </p>
                    </div>
                    <div className="text-right text-xs">
                      <div className="font-semibold">{tool.risk_level}</div>
                      <div className="mt-1 text-[var(--ink-muted)]">
                        {tool.provider}
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 flex gap-4 text-[11px] text-[var(--ink-muted)]">
                    <span>Category: {tool.category}</span>
                    <span>Side effect: {tool.side_effect_type ?? "none"}</span>
                    <span>
                      Confirmation: {tool.requires_confirmation ? "required" : "no"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="panel overflow-hidden">
            <SectionHeader icon={<ShieldCheck size={17} />} title="AgentGuard Integration" />
            <div className="grid grid-cols-2 gap-px bg-[var(--border)]">
              <IntegrationFact
                icon={<ShieldCheck size={16} />}
                label="Policy"
                value={config.guardrails.policy_id}
              />
              <IntegrationFact
                icon={<RadioTower size={16} />}
                label="Trace namespace"
                value={config.guardrails.trace_namespace}
              />
              <IntegrationFact
                icon={<CheckCircle2 size={16} />}
                label="Approval enforcement"
                value={config.guardrails.approval_enforced ? "Enabled" : "Disabled"}
              />
              <IntegrationFact
                icon={<KeyRound size={16} />}
                label="Gemini credentials"
                value={
                  config.runtime.model_credentials_configured
                  ? "Configured"
                  : "Not configured"
                }
              />
              <IntegrationFact
                icon={<Wrench size={16} />}
                label="Gmail MCP"
                value={
                  config.runtime.gmail_mcp_ready
                    ? "Ready"
                    : config.runtime.gmail_mcp_detail
                }
              />
            </div>
            <div className="border-t border-[var(--border)] p-5">
              <div className="rounded border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
                {config.guardrails.implementation}
              </div>
              <div className="eyebrow">Callbacks</div>
              <div className="mt-3 space-y-2">
                {config.callbacks.map((callback) => (
                  <div className="font-mono text-xs" key={callback}>
                    {callback}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        <section className="panel h-fit overflow-hidden">
          <SectionHeader icon={<FlaskConical size={17} />} title="Test Agent" />
          <div className="space-y-4 p-5">
            <p className="text-sm text-[var(--ink-muted)]">
              Runs the real Google ADK agent. Proposed tool calls pass through
              AgentGuard before execution.
            </p>
            <div>
              <div className="eyebrow">Test scenarios</div>
              <div className="mt-2 grid gap-2">
                {config.test_scenarios.map((scenario) => (
                  <button
                    className="rounded border border-[var(--border)] bg-white p-3 text-left hover:border-[var(--blue)]"
                    key={scenario.id}
                    onClick={() => setMessage(scenario.prompt)}
                  >
                    <div className="text-sm font-semibold">{scenario.name}</div>
                    <div className="mt-1 text-xs text-[var(--ink-muted)]">
                      {scenario.expected_behavior}
                    </div>
                  </button>
                ))}
              </div>
            </div>
            <textarea
              className="min-h-32 w-full resize-y rounded border border-[var(--border)] bg-white p-3 text-sm outline-none focus:border-[var(--blue)]"
              placeholder="Enter a message for the Google ADK agent..."
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            <button
              className="flex w-full items-center justify-center gap-2 rounded bg-black px-4 py-3 text-sm font-semibold text-white disabled:opacity-40"
              disabled={!message.trim() || testRun.isPending}
              onClick={() => testRun.mutate()}
            >
              <Play size={16} fill="currentColor" />
              {testRun.isPending ? "Running Google ADK..." : "Run Test"}
            </button>

            {testRun.error && (
              <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                {testRun.error.message}
              </div>
            )}

            {testRun.data && (
              <div className="space-y-4 border-t border-[var(--border)] pt-5">
                <div>
                  <div className="eyebrow">Agent response</div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6">
                    {testRun.data.final_response}
                  </p>
                </div>
                <div>
                  <div className="eyebrow">AgentGuard decisions</div>
                  <div className="mt-2 space-y-2">
                    {testRun.data.decisions.length ? (
                      testRun.data.decisions.map((decision) => (
                        <div
                          className="rounded border border-[var(--border)] p-3"
                          key={decision.trace_id}
                        >
                          <div className="flex items-center justify-between">
                            <code className="text-xs font-semibold">
                              {decision.tool_name}
                            </code>
                            <StatusBadge value={decision.decision} />
                          </div>
                          <div className="mt-2 text-xs text-[var(--ink-muted)]">
                            Risk {Math.round(decision.risk_score * 100)} ·{" "}
                            {decision.explanation}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded bg-[var(--surface-low)] p-3 text-xs text-[var(--ink-muted)]">
                        No tool call was proposed in this turn.
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-[11px] text-[var(--ink-muted)]">
                  Session <code>{testRun.data.session_id}</code> ·{" "}
                  {testRun.data.duration_ms}ms
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function SectionHeader({
  icon,
  title,
}: {
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <div className="flex h-14 items-center gap-2 border-b border-[var(--border)] px-5">
      {icon}
      <h3 className="text-sm font-bold">{title}</h3>
    </div>
  );
}

function DefinitionFact({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className="mt-1 font-mono text-xs">{value ?? "Not available"}</div>
    </div>
  );
}

function IntegrationFact({
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
      <div className="mt-2 font-mono text-xs font-semibold">{value}</div>
    </div>
  );
}
