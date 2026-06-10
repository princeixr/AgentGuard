export type Decision =
  | "allow"
  | "warn"
  | "review"
  | "require_approval"
  | "block";

export interface GuardEvaluation {
  firewall_mode: string;
  firewall_version: string;
  enforcement_status: string;
  recommendation: Decision;
  enforced_by: string;
  explanation: string;
  policy_id: string | null;
  policy_version: string | null;
  policy_hash: string | null;
  matched_rules: Array<{
    rule_id: string;
    effect: string;
    description?: string;
    matched_capabilities?: string[];
    matched_resources?: string[];
  }>;
  deferred_rule_ids: string[];
  normalized_action: Record<string, any> | null;
  tier_results: Array<Record<string, any>>;
  combined_decision: Record<string, any> | null;
  stages: Array<{
    name: string;
    status: string;
    detail: string;
  }>;
}

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
  guard_evaluation: GuardEvaluation | null;
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
  guard_evaluation: GuardEvaluation | null;
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
  event_source: string;
  firewall_mode: string;
  guard_version: string;
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
  domain: string;
  operation: string;
  capabilities: string[];
  impact: string;
  reversible: boolean | null;
  normalizer: string;
  metadata_status: string;
  metadata_confidence: number;
  metadata_provenance: string[];
  argument_roles: Record<string, string[]>;
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
    policy_version: string;
    policy_hash: string;
    policy_status: string;
    firewall_mode: string;
    enforced_by: string;
    v2_status: string;
    implementation: string;
    approval_enforced: boolean;
    trace_namespace: string;
  };
  runtime: {
    model_credentials_configured: boolean;
    mcp_config_path: string;
    mcp_servers: Array<{
      id: string;
      prefix: string;
      transport: string;
      enabled: boolean;
      ready: boolean;
      detail: string;
    }>;
  };
  test_scenarios: AgentTestScenario[];
}

export interface GuardAdminComponent {
  component_id: string;
  name: string;
  layer: string;
  status:
    | "operational"
    | "observe_only"
    | "placeholder"
    | "not_implemented";
  summary: string;
  management: string;
}

export interface GuardAdminStatus {
  agent_id: string;
  firewall_mode: string;
  active_enforcement: string;
  architecture_version: string;
  force_block_enabled: boolean;
  approval_enforced: boolean;
  policy: {
    policy_id: string;
    status: "placeholder" | "operational";
    source: string;
    editable: boolean;
    explanation: string;
    version: string | null;
    effective_hash: string | null;
    rule_count: number;
    defaults: Record<string, string>;
  };
  components: GuardAdminComponent[];
  tools: AgentToolDefinition[];
  warnings: string[];
}

export interface AgentPolicy {
  policy_id: string;
  version: string;
  status: string;
  effective_hash: string;
  source: string;
  validation: "valid";
  document: {
    schema_version: string;
    policy_id: string;
    version: string;
    name: string;
    description: string;
    status: "draft" | "published";
    scope: {
      workspace_id: string;
      agent_id: string;
      deployment_id: string | null;
    };
    defaults: Record<string, string>;
    routing: Record<string, string[]>;
    rules: Array<{
      rule_id: string;
      description: string;
      effect: "allow" | "require_approval" | "block";
      severity: string;
      non_overridable: boolean;
      match: {
        capabilities_any: string[];
        tools_any: string[];
        resource_constraints: Record<string, unknown>;
      };
    }>;
    notes: string[];
  };
}

export interface PolicyValidation {
  valid: boolean;
  policy_id: string | null;
  version: string | null;
  effective_hash: string | null;
  errors: string[];
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
    guard_evaluation: GuardEvaluation | null;
  }>;
  duration_ms: number;
}
