from agentguard.core.enums import ToolRiskLevel
from agentguard.firewall_v2.config import FirewallV2RuntimeConfig
from agentguard.firewall_v2.engine import AgentGuardFirewallV2
from agentguard.firewall_v2.tools.registry import descriptor_for_tool
from agentguard.runtime.tool_registry import ToolMetadata
from agentguard.tracing.schema_v1 import TraceSourceV1
from agentguard.tracing.trace_v1_builder import TraceV1BuildInput, TraceV1Builder


class FailingJudgeProvider:
    def judge(self, packet):
        raise AssertionError("Tier 3 must not run after deterministic approval.")


def _gmail_send_trace():
    return TraceV1Builder().build(
        TraceV1BuildInput(
            session_id="approval_short_circuit",
            step_index=1,
            source=TraceSourceV1(
                mode="live",
                agent_framework="google_adk",
                source_type="test",
                agent_id="test_agent",
            ),
            raw_user_request="Send the event details by email.",
            normalized_intent="Send the event details by email.",
            domain="email",
            task_category="email_send",
            tool_name="workspace_gmail_send",
            arguments={
                "to": "recipient@example.com",
                "subject": "Event details",
                "body": "Details",
            },
            available_tools=["workspace_gmail_send"],
            task_relevant_tools=["workspace_gmail_send"],
            confirmation_required_tools=["workspace_gmail_send"],
        )
    )


def _gmail_send_descriptor(tool_name: str):
    metadata = ToolMetadata(
        name=tool_name,
        category="email",
        risk_level=ToolRiskLevel.EXTERNAL_WRITE,
        side_effect_type="external_message_send",
        requires_confirmation_by_default=True,
        irreversible=False,
        provider="google_workspace",
        description="Send an email through Gmail.",
        operation="send",
        capabilities=("email.send",),
        argument_roles={
            "destinations": ("to",),
            "data": ("subject", "body"),
        },
        required_arguments=("to", "subject", "body"),
        external_impact=True,
        metadata_confidence=0.85,
        metadata_provenance=("test_registration",),
    )
    return descriptor_for_tool(tool_name, metadata)


def test_deterministic_approval_skips_later_tiers():
    evaluation = AgentGuardFirewallV2(
        mode="v2",
        runtime_config=FirewallV2RuntimeConfig(
            agenttrust_shell_enabled=False,
            tier_3_enabled=True,
            tier_3_enforcement_enabled=True,
        ),
        tier_3_provider=FailingJudgeProvider(),
        descriptor_resolver=_gmail_send_descriptor,
    ).evaluate(_gmail_send_trace())

    assert evaluation.recommendation == "require_approval"
    assert evaluation.combined_decision["enforced_by"] == "deterministic_policy"
    assert [result["tier"] for result in evaluation.tier_results] == ["tier_1"]
