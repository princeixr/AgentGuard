import type {
  Agent,
  AgentDefinition,
  AgentPolicy,
  CurrentInterception,
  GuardAdminStatus,
  MemoryDetail,
  MemoryPage,
  OperationsSummary,
  PendingApproval,
  PolicyValidation,
  SessionDetail,
  SessionSummary,
  WorkspaceContext,
} from "./types";

// ── Auth token storage ────────────────────────────────────────────────────────

export function getAuthToken(): string {
  return window.localStorage.getItem("agentguard.authToken") ?? "";
}

export function setAuthToken(token: string): void {
  window.localStorage.setItem("agentguard.authToken", token);
}

export function clearAuthToken(): void {
  window.localStorage.removeItem("agentguard.authToken");
  window.localStorage.removeItem("agentguard.workspaceId");
  window.localStorage.removeItem("agentguard.userId");
  window.localStorage.removeItem("agentguard.email");
}

export function isAuthenticated(): boolean {
  return Boolean(getAuthToken());
}

/** Legacy API key (kept for backwards compat with agent-as-operator flows). */
export function getApiKey(): string {
  return (
    window.localStorage.getItem("agentguard.apiKey") ??
    import.meta.env.VITE_AGENTGUARD_API_KEY ??
    ""
  );
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  // Prefer JWT; fall back to legacy API key
  const token = getAuthToken() || getApiKey();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

// ── Auth endpoints ────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  workspace_id: string;
  user_id: string;
  email: string;
}

export interface MeResponse {
  user_id: string;
  email: string;
  workspace_id: string;
}

export const authApi = {
  register: (email: string, password: string) =>
    request<AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<MeResponse>("/api/v1/auth/me"),
};

// ── Agent token management endpoints ─────────────────────────────────────────

export interface TokenInfo {
  key_id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
}

export interface CreatedToken extends TokenInfo {
  token: string;
}

export const tokensApi = {
  list: () =>
    request<{ items: TokenInfo[] }>("/api/v1/tokens"),

  create: (name: string) =>
    request<CreatedToken>("/api/v1/tokens", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  revoke: (keyId: string) =>
    fetch(`/api/v1/tokens/${encodeURIComponent(keyId)}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getAuthToken() || getApiKey()}` },
    }),
};

// ── Existing dashboard API ────────────────────────────────────────────────────

export const api = {
  me: () => request<WorkspaceContext>("/api/v1/me"),
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
  currentInterception: (agentId: string) =>
    request<CurrentInterception>(
      `/api/v1/agents/${encodeURIComponent(agentId)}/interceptions/current`,
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
  approvals: (status: PendingApproval["status"] | "all" = "pending") =>
    request<{ items: PendingApproval[] }>(
      `/api/v1/approvals?status=${encodeURIComponent(status)}`,
    ),
  approve: (approvalId: string, note?: string) =>
    request<PendingApproval>(
      `/api/v1/approvals/${encodeURIComponent(approvalId)}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ actor: "operator", note }),
      },
    ),
  reject: (approvalId: string, note?: string) =>
    request<PendingApproval>(
      `/api/v1/approvals/${encodeURIComponent(approvalId)}/reject`,
      {
        method: "POST",
        body: JSON.stringify({ actor: "operator", note }),
      },
    ),
};
