import type {
  Agent,
  AgentDefinition,
  AgentPolicy,
  AgentTestRun,
  CurrentInterception,
  DemoSessionContext,
  GuardAdminStatus,
  MemoryDetail,
  MemoryPage,
  OperationsSummary,
  PolicyValidation,
  Scenario,
  SessionDetail,
  SessionSummary,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<DemoSessionContext>("/api/v1/me"),
  agents: () => request<{ items: Agent[] }>("/api/v1/agents"),
  agent: (agentId: string) =>
    request<Agent>(`/api/v1/agents/${encodeURIComponent(agentId)}`),
  agentDefinition: (agentId: string) =>
    request<AgentDefinition>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/definition`,
    ),
  guardAdmin: (agentId: string) =>
    request<GuardAdminStatus>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/guard`,
    ),
  agentPolicy: (agentId: string) =>
    request<AgentPolicy>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/policy`,
    ),
  validateAgentPolicy: (agentId: string, document: Record<string, unknown>) =>
    request<PolicyValidation>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/policy/validate`,
      {
        method: "POST",
        body: JSON.stringify({ document }),
      },
    ),
  updateAgentPolicy: (
    agentId: string,
    expectedHash: string,
    document: Record<string, unknown>,
  ) =>
    request<AgentPolicy>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/policy`,
      {
        method: "PUT",
        body: JSON.stringify({ expected_hash: expectedHash, document }),
      },
    ),
  runAgentTest: (agentId: string, message: string) =>
    request<AgentTestRun>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/test-runs`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
    ),
  sessions: (agentId: string) =>
    request<SessionSummary[]>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/sessions`,
    ),
  session: (agentId: string, id: string) =>
    request<SessionDetail>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/sessions/${encodeURIComponent(id)}`,
    ),
  memory: (agentId: string, params: URLSearchParams) =>
    request<MemoryPage>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/memory?${params.toString()}`,
    ),
  memoryDetail: (agentId: string, id: string) =>
    request<MemoryDetail>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/memory/${encodeURIComponent(id)}`,
    ),
  operations: (agentId: string) =>
    request<OperationsSummary>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/operations/summary`,
    ),
  scenarios: () =>
    request<{ items: Scenario[] }>("/api/v1/demo/scenarios"),
  currentInterception: (agentId: string) =>
    request<CurrentInterception>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/interceptions/current`,
    ),
  startScenario: (agentId: string, id: string) =>
    request<{ scenario_id: string; session_id: string; status: string }>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/demo/scenarios/${encodeURIComponent(id)}/start`,
      { method: "POST" },
    ),
  resolveApproval: (
    agentId: string,
    traceId: string,
    action: "approve" | "reject" | "abort",
  ) =>
    request(
      `/api/v1/agents/${encodeURIComponent(agentId)}/approvals/${encodeURIComponent(traceId)}`,
      {
        method: "POST",
        body: JSON.stringify({ action }),
      },
    ),
  resetDemo: () => request("/api/v1/demo/reset", { method: "POST" }),
};
