import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bot,
  ExternalLink,
  Fingerprint,
  RadioTower,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";

export function AgentDetailPage() {
  const { agentId = "" } = useParams();
  const agent = useQuery({
    queryKey: ["agent", agentId],
    queryFn: () => api.agent(agentId),
    enabled: Boolean(agentId),
  });
  const definition = useQuery({
    queryKey: ["agent-definition", agentId],
    queryFn: () => api.agentDefinition(agentId),
    enabled: Boolean(agentId),
  });

  if (agent.isLoading || definition.isLoading) {
    return <LoadingState label="Loading registered agent" />;
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
        <div className="flex gap-2">
          {config.agent_ui_url && (
            <a
              className="flex items-center gap-2 rounded border border-[var(--border)] bg-white px-4 py-2 text-xs font-semibold"
              href={config.agent_ui_url}
              rel="noreferrer"
              target="_blank"
            >
              Open agent UI
              <ExternalLink size={14} />
            </a>
          )}
          <Link
            className="rounded bg-[var(--blue)] px-4 py-2 text-xs font-semibold text-white"
            to={`/agents/${agentId}/trace-interception`}
          >
            Open guard dashboard
          </Link>
        </div>
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
                {agent.data.description}
              </p>
              <code className="mt-3 block text-xs text-[var(--ink-muted)]">
                {agentId}
              </code>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-xs">
            <DefinitionFact label="Framework" value={config.framework} />
            <DefinitionFact label="Runtime version" value={config.runtime_version} />
            <DefinitionFact
              label="Environment"
              value={deployment?.environment ?? config.environment}
            />
            <DefinitionFact label="Manifest" value={config.manifest_version} />
          </div>
        </div>
      </section>

      <div className="grid grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)] gap-5">
        <section className="panel overflow-hidden">
          <SectionHeader icon={<Wrench size={17} />} title="Registered Tool Manifest" />
          <div className="divide-y divide-[var(--border)]">
            {config.tools.length ? (
              config.tools.map((tool) => (
                <div className="p-5" key={tool.name}>
                  <div className="flex items-start justify-between gap-5">
                    <div>
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-bold">{tool.name}</code>
                        <StatusBadge value={tool.metadata_status} />
                      </div>
                      <p className="mt-2 text-sm text-[var(--ink-muted)]">
                        {tool.description || "No description was registered."}
                      </p>
                    </div>
                    <div className="text-right text-xs">
                      <div className="font-semibold">{tool.impact} impact</div>
                      <div className="mt-1 text-[var(--ink-muted)]">{tool.provider}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {tool.capabilities.map((capability) => (
                      <span
                        className="rounded border border-[var(--border)] bg-[var(--surface-low)] px-2 py-1 font-mono text-[10px]"
                        key={capability}
                      >
                        {capability}
                      </span>
                    ))}
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-3 text-[11px] text-[var(--ink-muted)]">
                    <span>Action: {tool.domain}.{tool.operation}</span>
                    <span>Normalizer: {tool.normalizer}</span>
                    <span>Confidence: {Math.round(tool.metadata_confidence * 100)}%</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-5 text-sm text-[var(--ink-muted)]">
                No tools have been registered by this agent.
              </div>
            )}
          </div>
        </section>

        <div className="space-y-5">
          <section className="panel overflow-hidden">
            <SectionHeader icon={<Fingerprint size={17} />} title="Registration" />
            <div className="grid gap-px bg-[var(--border)]">
              <RegistrationFact label="Deployment" value={config.deployment_id} />
              <RegistrationFact label="Integration" value={config.integration_id} />
              <RegistrationFact
                label="Instruction hash"
                value={config.system_instruction_hash ?? "Not supplied"}
              />
            </div>
            {config.system_instruction_summary && (
              <div className="border-t border-[var(--border)] p-5">
                <div className="eyebrow">Instruction summary</div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
                  {config.system_instruction_summary}
                </p>
              </div>
            )}
          </section>

          <section className="panel overflow-hidden">
            <SectionHeader icon={<ShieldCheck size={17} />} title="Product Boundary" />
            <div className="space-y-3 p-5 text-sm leading-6 text-[var(--ink-muted)]">
              <p>
                AgentGuard stores this sanitized registration manifest. It does not
                host the agent, read MCP credentials, or execute agent tools.
              </p>
              <p>
                Live decisions will appear after the independent agent connects
                through the AgentGuard SDK transport.
              </p>
              <div className="flex items-center gap-2 rounded bg-[var(--surface-low)] p-3 text-xs">
                <RadioTower size={15} />
                Transport status:{" "}
                <strong>{String(deployment?.metadata.transport ?? "unknown")}</strong>
              </div>
            </div>
          </section>
        </div>
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

function RegistrationFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-4">
      <div className="eyebrow">{label}</div>
      <div className="mt-2 break-all font-mono text-xs font-semibold">{value}</div>
    </div>
  );
}
