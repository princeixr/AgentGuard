from agentguard import __version__
from agentguard_sdk import agent_facing_enforcement_message


def test_backend_and_sdk_are_importable():
    assert __version__ == "0.1.0"
    assert agent_facing_enforcement_message("block").startswith(
        "AgentGuard blocked this tool call"
    )
