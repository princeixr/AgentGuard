import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  AgentPolicy,
  PendingApproval,
  ReplayStep,
} from "../../api/types";
import {
  IntentContractContext,
  InterceptionDetail,
  SessionQueryContext,
} from "./LivePage";

const approvalStep: ReplayStep = {
  trace_id: "trace-1",
  step_index: 1,
  timestamp: "2026-06-10T22:00:00Z",
  tool_name: "run_shell_command",
  tool_category: "filesystem",
  arguments: { command: "rm ~/Downloads/report.pdf" },
  argument_summary: 'command="rm ~/Downloads/report.pdf"',
  decision: "require_approval",
  risk_score: 0.7,
  component_scores: {},
  cumulative_risk: 0.7,
  dominant_signals: [],
  rules_fired: [],
  explanation: "Approval is required.",
  execution_status: "proposed",
  output_summary: null,
  guard_evaluation: {
    firewall_mode: "v2",
    firewall_version: "agentguard_firewall_v2",
    enforcement_status: "enforced",
    recommendation: "require_approval",
    enforced_by: "combiner_low_confidence_fallback",
    explanation: "The semantic evaluator did not return sufficient confidence.",
    policy_id: "policy-1",
    policy_version: "1.0.0",
    policy_hash: null,
    matched_rules: [],
    deferred_rule_ids: [],
    normalized_action: {
      operation: "delete",
      resources: [{ value: "~/Downloads/report.pdf" }],
    },
    intent_contract: {
      raw_user_request: "List files in Downloads.",
      requested_capabilities: ["filesystem.read"],
      forbidden_capabilities: ["filesystem.delete"],
      permitted_resources: ["~/Downloads"],
      extractor: {
        name: "intent_extractor",
        confidence: 0.82,
      },
    },
    intent_authorization: {
      recommendation: "block",
      unauthorized_capabilities: ["filesystem.delete"],
    },
    evaluation_plan: null,
    tier_results: [
      {
        tier: "tier_2",
        status: "not_available",
        recommendation: "not_available",
        explanation: "Tier 2 semantic retrieval is not implemented.",
      },
    ],
    combined_decision: {
      enforced_by: "combiner_low_confidence_fallback",
    },
    stages: [],
  },
};

const policy: AgentPolicy = {
  policy_id: "policy-1",
  version: "1.0.0",
  status: "published",
  effective_hash: "hash-1",
  source: "test",
  validation: "valid",
  document: {
    schema_version: "agentguard.policy.v1",
    policy_id: "policy-1",
    version: "1.0.0",
    name: "Test policy",
    description: "Test policy",
    status: "published",
    scope: {
      workspace_id: "workspace-1",
      agent_id: "agent-1",
      deployment_id: null,
    },
    defaults: {},
    routing: {},
    rules: [
      {
        rule_id: "approval-write",
        description: "Writes need approval",
        effect: "require_approval",
        severity: "medium",
        non_overridable: false,
        match: {
          capabilities_any: ["filesystem.write"],
          tools_any: [],
          resource_constraints: {},
        },
      },
      {
        rule_id: "block-delete",
        description: "Deletes are blocked",
        effect: "block",
        severity: "high",
        non_overridable: true,
        match: {
          capabilities_any: ["filesystem.delete"],
          tools_any: [],
          resource_constraints: {},
        },
      },
    ],
    notes: [],
  },
};

const approved: PendingApproval = {
  approval_id: "approval-1",
  decision_id: "decision-1",
  trace_id: approvalStep.trace_id,
  call_id: "call-1",
  workspace_id: "workspace-1",
  agent_id: "agent-1",
  deployment_id: "deployment-1",
  integration_id: "integration-1",
  session_id: "session-1",
  turn_id: "turn-1",
  tool_name: approvalStep.tool_name,
  arguments: approvalStep.arguments,
  user_request: "List files in Downloads.",
  explanation: "Approval is required.",
  guard_evaluation: approvalStep.guard_evaluation,
  status: "approved",
  created_at: "2026-06-10T22:00:00Z",
  resolved_at: "2026-06-10T22:00:05Z",
  resolved_by: "operator",
  note: null,
};

describe("InterceptionDetail", () => {
  it("presents the verdict and intent gap before collapsed technical payloads", () => {
    const { container } = render(
      <InterceptionDetail
        evidenceLoading={false}
        precedents={[]}
        step={approvalStep}
        userIntent="List files in Downloads."
      />,
    );

    expect(
      screen.getByRole("heading", { name: "require approval" }),
    ).toBeInTheDocument();
    expect(container.querySelector(".verdict-evaluator"))
      .toHaveTextContent("combiner_low_confidence_fallback");
    expect(screen.queryByText(/agentguard_firewall_v2/)).not.toBeInTheDocument();
    expect(screen.getByText("User requested")).toBeInTheDocument();
    expect(screen.getByText("Agent attempted")).toBeInTheDocument();
    expect(screen.queryByText("scope violation")).not.toBeInTheDocument();
    expect(screen.queryByText("within scope")).not.toBeInTheDocument();
    expect(container.querySelector(".intent-action-section"))
      .toBeInTheDocument();
    expect(
      screen.getByText(/No explicit enforcing rule produced this verdict/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Tier 2 semantic retrieval is not implemented."),
    ).toBeInTheDocument();

    const disclosures = container.querySelectorAll("details");
    expect(disclosures).toHaveLength(2);
    disclosures.forEach((disclosure) => {
      expect(disclosure).not.toHaveAttribute("open");
      expect(disclosure).toHaveAttribute("name", "live-interception-detail");
    });
  });

  it("shows a resolved approval as an approved blue verdict", () => {
    const { container } = render(
      <InterceptionDetail
        approval={approved}
        evidenceLoading={false}
        precedents={[]}
        step={approvalStep}
        userIntent="List files in Downloads."
      />,
    );

    expect(
      screen.getByRole("heading", { name: "approved" }),
    ).toBeInTheDocument();
    expect(container.querySelector(".verdict-hero-approved")).toBeInTheDocument();
  });
});

describe("SessionContext", () => {
  it("stays frozen for one session and regenerates for a new session", () => {
    const { container, rerender } = render(
      <>
        <SessionQueryContext
          key="query-session-1"
          policy={policy}
          sessionId="session-1"
          sourceStep={approvalStep}
          userQuery="List files in Downloads."
        />
        <IntentContractContext
          key="contract-session-1"
          policy={policy}
          sessionId="session-1"
          sourceStep={approvalStep}
          userQuery="List files in Downloads."
        />
      </>,
    );
    const context = within(container);

    expect(context.getByText("List files in Downloads.", { exact: false }))
      .toBeInTheDocument();
    expect(context.getByText("filesystem.read")).toBeInTheDocument();
    expect(context.getByText("filesystem.write")).toBeInTheDocument();
    expect(context.getAllByText("filesystem.delete")).toHaveLength(1);
    expect(context.getByText("SCOPE_DEFINED")).toBeInTheDocument();
    const contract = context.getByLabelText("Intent Contract");
    expect(contract).not.toHaveAttribute("open");
    expect(contract).toHaveAttribute("name", "live-interception-detail");
    expect(contract?.querySelector(".contract-rows")).toBeInTheDocument();

    const changedStep = {
      ...approvalStep,
      guard_evaluation: {
        ...approvalStep.guard_evaluation!,
        intent_contract: {
          raw_user_request: "Changed trace data",
          requested_capabilities: ["email.send"],
        },
      },
    };
    rerender(
      <>
        <SessionQueryContext
          key="query-session-1"
          policy={policy}
          sessionId="session-1"
          sourceStep={changedStep}
          userQuery="Changed trace data"
        />
        <IntentContractContext
          key="contract-session-1"
          policy={policy}
          sessionId="session-1"
          sourceStep={changedStep}
          userQuery="Changed trace data"
        />
      </>,
    );
    expect(context.queryByText("Changed trace data", { exact: false }))
      .not.toBeInTheDocument();

    rerender(
      <>
        <SessionQueryContext
          key="query-session-2"
          policy={policy}
          sessionId="session-2"
          sourceStep={changedStep}
          userQuery="Changed trace data"
        />
        <IntentContractContext
          key="contract-session-2"
          policy={policy}
          sessionId="session-2"
          sourceStep={changedStep}
          userQuery="Changed trace data"
        />
      </>,
    );
    expect(context.getByText("Changed trace data", { exact: false }))
      .toBeInTheDocument();
  });
});
