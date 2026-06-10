from agentguard.firewall_v2.tools.registry import descriptor_for_tool
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.intent.extractor import IntentExtractor, deterministic_intent_fallback
from agentguard.intent.models import IntentExtractionPayloadV1


class _StructuredProvider:
    model = "mock-structured-intent"

    def extract(self, user_request, tool_descriptors):
        return IntentExtractionPayloadV1(
            requested_capabilities=["email.search", "email.read", "email.draft"],
            forbidden_capabilities=["email.send"],
            destinations=["finance@example.com"],
            side_effect_authorized=True,
            confidence=0.96,
        )


def test_structured_provider_creates_schema_valid_turn_contract():
    contract = IntentExtractor(provider=_StructuredProvider()).extract(
        user_request=(
            "Find the budget email and draft a reply to finance@example.com. "
            "Do not send it."
        ),
        session_id="session_1",
        agent_id="agent_1",
        turn_id="turn_1",
        tool_descriptors=[
            descriptor_for_tool("gmail_search"),
            descriptor_for_tool("gmail_draft"),
            descriptor_for_tool("gmail_send"),
        ],
    )

    assert contract.turn_id == "turn_1"
    assert contract.requested_capabilities == [
        "email.draft",
        "email.read",
        "email.search",
    ]
    assert contract.forbidden_capabilities == ["email.send"]
    assert contract.extractor.method == "llm_structured"
    assert contract.extractor.model == "mock-structured-intent"


def test_deterministic_fallback_handles_explicit_do_not_send():
    payload = deterministic_intent_fallback(
        "Find the latest email, draft a reply, but do not send it.",
        [
            descriptor_for_tool("gmail_search"),
            descriptor_for_tool("gmail_draft"),
            descriptor_for_tool("gmail_send"),
        ],
    )

    assert "email.search" in payload.requested_capabilities
    assert "email.draft" in payload.requested_capabilities
    assert payload.forbidden_capabilities == ["email.send"]
    assert payload.side_effect_authorized is True


def test_deterministic_fallback_maps_ls_request_to_filesystem_inspection():
    payload = deterministic_intent_fallback(
        "Run the ls command.",
        [descriptor_for_tool("run_shell_command")],
    )

    assert payload.requested_capabilities == ["filesystem.inspect", "process.execute"]


def test_deterministic_fallback_does_not_map_generic_list_to_every_list_tool():
    payload = deterministic_intent_fallback(
        "List any 5 files in my downloads folder.",
        [
            descriptor_for_tool("run_shell_command"),
            ToolDescriptorV1(
                tool_name="workspace_calendar_list",
                provider="workspace",
                category="calendar",
                capabilities=["calendar.list"],
                normalizer="structured_v1",
            ),
            ToolDescriptorV1(
                tool_name="workspace_gmail_listLabels",
                provider="workspace",
                category="email",
                capabilities=["email.list"],
                normalizer="structured_v1",
            ),
        ],
    )

    assert payload.requested_capabilities == ["filesystem.inspect"]
