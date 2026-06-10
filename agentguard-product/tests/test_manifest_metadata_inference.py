from agentguard.control_plane.models import RegisteredTool
from agentguard.firewall_v2.tools.metadata_inference import (
    infer_registered_tool_metadata,
)


def test_manifest_inference_classifies_email_send_and_recipient():
    metadata = infer_registered_tool_metadata(
        RegisteredTool(
            name="gmail_send_email",
            source_name="send_email",
            provider="gmail",
            framework="google_adk",
            transport="mcp",
            description="Send an email to a recipient.",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "body"],
            },
        )
    )

    assert metadata.capabilities == ("email.send",)
    assert metadata.external_impact is True
    assert metadata.argument_roles["destination"] == ("to",)
    assert metadata.argument_roles["content"] == ("body",)


def test_unknown_manifest_fails_high_risk_and_low_confidence():
    metadata = infer_registered_tool_metadata(
        RegisteredTool(
            name="perform",
            source_name="perform",
            provider="custom",
            framework="custom",
            transport="function",
        )
    )

    assert metadata.operation == "unknown"
    assert metadata.metadata_confidence < 0.5
    assert metadata.requires_confirmation_by_default is True
