export type Decision =
  | "allow"
  | "warn"
  | "review"
  | "require_approval"
  | "block";

export interface ComponentHealth {
  name: string;
  status: "operational" | "degraded" | "unavailable";
  detail: string;
}

export interface SessionSummary {
  session_id: string;
  scenario_id: string | null;
  agent_id: string;
  agent_framework: string;
  user_intent: string;
  started_at: string;
  updated_at: string;
  step_count: number;
  final_decision: Decision;
  max_risk_score: number;
  tool_sequence: string[];
}

export interface ReplayStep {
  trace_id: string;
  step_index: number;
  timestamp: string;
  tool_name: string;
  tool_category: string;
  arguments: Record<string, unknown>;
  argument_summary: string;
  decision: Decision;
  risk_score: number;
  component_scores: Record<string, number>;
  cumulative_risk: number;
  dominant_signals: string[];
  rules_fired: string[];
  explanation: string;
  execution_status: string;
  output_summary: string | null;
}

export interface PrecedentSummary {
  trace_id: string;
  session_id: string;
  scenario_id: string | null;
  tool_name: string;
  decision: Decision;
  risk_score: number;
  intent: string;
}

export interface SessionDetail {
  session: SessionSummary;
  steps: ReplayStep[];
  precedents: PrecedentSummary[];
}

export interface MemoryItem {
  trace_id: string;
  session_id: string;
  timestamp: string;
  agent_id: string;
  agent_framework: string;
  scenario_id: string | null;
  domain: string;
  tool_name: string;
  tool_category: string;
  risk_score: number;
  decision: Decision;
  labels: string[];
  explanation: string;
}

export interface MemoryPage {
  items: MemoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface MemoryDetail {
  item: MemoryItem;
  trace: Record<string, any>;
  feature: Record<string, any>;
  score: Record<string, any>;
  decision: Record<string, any>;
  label: Record<string, any> | null;
  events: Array<Record<string, any>>;
  precedents: PrecedentSummary[];
}

export interface CurrentInterception {
  status: "idle" | "running" | "paused" | "completed";
  agent_id: string | null;
  scenario_id: string | null;
  session_id: string | null;
  current_trace_id: string | null;
  current_step: number;
  total_steps: number;
  approval: {
    trace_id: string;
    action: "approve" | "reject" | "abort";
    actor: string;
    note: string | null;
    timestamp: string;
  } | null;
  detail: MemoryDetail | null;
}

export interface OperationsSummary {
  intercepted_calls: number;
  intervention_count: number;
  intervention_rate: number;
  blocked_count: number;
  blocked_rate: number;
  session_count: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  riskiest_tools: Array<{ name: string; count: number; rate: number }>;
  failure_modes: Array<{ name: string; count: number; rate: number }>;
  health: ComponentHealth[];
}

export interface Scenario {
  scenario_id: string;
  domain: string;
  task_category: string;
  user_request: string;
  failure_type: string;
  gold_final_verdict: string;
}

export interface Deployment {
  deployment_id: string;
  workspace_id: string;
  agent_id: string;
  environment: string;
  runtime_framework: string;
  runtime_agent_name: string;
  version: string;
  status: "live" | "stale" | "offline";
  last_seen_at: string;
  metadata: Record<string, unknown>;
}

export interface Agent {
  agent_id: string;
  workspace_id: string;
  name: string;
  description: string;
  framework: string;
  status: "live" | "stale" | "offline" | "setup_required";
  created_at: string;
  created_by: string;
  default_policy_id: string;
  last_seen_at: string;
  metadata: Record<string, unknown>;
  deployments: Deployment[];
}

export interface DemoSessionContext {
  user: {
    user_id: string;
    workspace_id: string;
    name: string;
    email: string;
    role: string;
  };
  workspace: {
    workspace_id: string;
    name: string;
    plan: string;
    created_at: string;
  };
}

export interface AgentToolDefinition {
  name: string;
  description: string;
  category: string;
  risk_level: string;
  side_effect_type: string | null;
  requires_confirmation: boolean;
  irreversible: boolean;
  enabled: boolean;
  provider: string;
}

export interface AgentTestScenario {
  id: string;
  name: string;
  prompt: string;
  expected_behavior: string;
}

export interface AgentDefinition {
  agent_id: string;
  runtime_name: string;
  app_name: string;
  framework: string;
  model: string;
  description: string;
  system_instruction: string;
  tools: AgentToolDefinition[];
  callbacks: string[];
  guardrails: {
    policy_id: string;
    implementation: string;
    approval_enforced: boolean;
    trace_namespace: string;
  };
  runtime: {
    model_credentials_configured: boolean;
    gmail_mcp_enabled: boolean;
    gmail_mcp_ready: boolean;
    gmail_mcp_detail: string;
    gmail_mcp_image: string;
  };
  test_scenarios: AgentTestScenario[];
}

export interface AgentTestRun {
  run_id: string;
  session_id: string;
  status: "completed" | "failed";
  model: string;
  user_message: string;
  final_response: string;
  events: Array<{
    type: "tool_call" | "tool_response" | "agent_response";
    name: string | null;
    content: string | null;
    arguments: Record<string, unknown> | null;
    response: unknown;
  }>;
  decisions: Array<{
    trace_id: string;
    tool_name: string;
    decision: Decision;
    risk_score: number;
    explanation: string;
    rules_fired: string[];
  }>;
  duration_ms: number;
}
