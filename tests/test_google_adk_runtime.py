from __future__ import annotations

import importlib
import json
from types import SimpleNamespace

import pytest

from fastapi import HTTPException

from agentguard.api.models import PolicyUpdateRequest, PolicyValidationRequest
from agentguard.api.repositories.local import LocalDashboardRepository
from agentguard.api.routes.agents import (
    get_agent_policy,
    update_agent_policy,
    validate_agent_policy,
)
from agentguard.api.services.query import DashboardQueryService
from agentguard.control_plane.registry import (
    DEMO_AGENT_ID,
    DEMO_DEPLOYMENT_ID,
    DEMO_INTEGRATION_ID,
    DEMO_WORKSPACE_ID,
    DemoAgentRegistry,
)
from agentguard.api.services.guard_admin import guard_admin_status
from agentguard.governance.session_risk_v1 import SessionRiskManagerV1
from agentguard.firewall_v2.policy.evaluator import PolicyEvaluatorV1
from agentguard.firewall_v2.policy.loader import PolicyLoader
from agentguard.firewall_v2.policy.models import PolicyDocumentV1
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy
from agentguard.firewall_v2.policy.store import PolicyStore
from agentguard.firewall_v2.policy.validator import PolicyValidationError
from agentguard.runtime.google_adk_adapter import GoogleADKTraceSession, adk_runtime_policy
from agentguard.runtime.mcp_registry import McpRegistry
from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.shell import ShellNormalizerV1
from agentguard.firewall_v2.tools.registry import descriptor_for_tool
from agentguard.tracing.serializers import load_jsonl
from agentguard.tracing.trace_store import TraceStore


@pytest.fixture(autouse=True)
def _stable_guard_environment(monkeypatch):
    monkeypatch.setenv("AGENTGUARD_FORCE_BLOCK", "false")
    monkeypatch.setenv("FORCE_BLOCK", "false")
    monkeypatch.setenv("AGENTGUARD_FIREWALL_MODE", "v1")


def test_google_adk_trace_session_runs_firewall_before_execution(tmp_path):
    session = GoogleADKTraceSession(
        session_id="adk_test_session",
        agent_id="terminal_assistant",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        available_tools=["run_shell_command", "workspace_gmail_send"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="google_adk_test",
        metadata_resolver=_mcp_registry().metadata_for,
    )
    session.start_turn("Draft a reply but do not send it.")

    result = session.record_tool_call(
        "workspace_gmail_send",
        {"to": "finance@example.com", "body": "Draft body"},
        call_id="call_001",
    )

    assert adk_runtime_policy(result.decision.decision) in {"require_approval", "block"}
    assert result.decision.decision in {"require_approval", "block"}
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "traces.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "features.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "scores.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "decisions.jsonl").exists()
    assert (tmp_path / "traces" / "v1" / "google_adk_test" / "session_risk").exists()


def test_google_adk_trace_session_propagates_runtime_identity(tmp_path):
    session = GoogleADKTraceSession(
        session_id="adk_owned_session",
        agent_id="runtime_alias",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        runtime_identity=DemoAgentRegistry().runtime_identity(DEMO_AGENT_ID),
        available_tools=["run_shell_command"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="google_adk_test",
    )
    session.start_turn("Show me the current directory.")

    result = session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_owned",
    )

    assert result.trace.source.workspace_id == DEMO_WORKSPACE_ID
    assert result.trace.source.agent_id == DEMO_AGENT_ID
    assert result.trace.source.deployment_id == DEMO_DEPLOYMENT_ID
    assert result.trace.source.integration_id == DEMO_INTEGRATION_ID
    assert result.feature.agent_id == DEMO_AGENT_ID
    assert result.score.agent_id == DEMO_AGENT_ID
    assert result.decision.agent_id == DEMO_AGENT_ID


def test_session_risk_state_restores_from_persisted_namespace(tmp_path):
    trace_store = TraceStore(root_dir=tmp_path / "traces")
    session = GoogleADKTraceSession(
        session_id="persisted_session",
        agent_id="terminal_assistant",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        available_tools=["run_shell_command"],
        trace_store=trace_store,
        namespace="google_adk_test",
    )
    session.start_turn("Show me the current directory.")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_persisted",
    )

    restored = SessionRiskManagerV1(
        trace_store=trace_store,
        namespace="google_adk_test",
    ).get("persisted_session")

    assert restored is not None
    assert restored.last_trace_id == result.trace.trace_id
    assert restored.tool_sequence == ["run_shell_command"]


def test_tool_descriptors_mark_known_and_unknown_tools_truthfully():
    shell = descriptor_for_tool("run_shell_command")
    gmail_send = descriptor_for_tool("gmail_send_email")
    unknown = descriptor_for_tool("custom_payment_tool")

    assert shell.capabilities == ["dynamic.shell"]
    assert shell.impact == "dynamic"
    assert shell.normalizer == "shell_v1"
    assert shell.metadata_status == "built_in"
    assert gmail_send.capabilities == ["email.send"]
    assert gmail_send.impact == "high"
    assert gmail_send.reversible is False
    assert unknown.capabilities == ["unknown"]
    assert unknown.normalizer == "unsupported"
    assert unknown.metadata_status == "unsupported"


def test_guard_admin_status_does_not_claim_unimplemented_v2_controls(monkeypatch):
    monkeypatch.setenv("AGENTGUARD_FIREWALL_MODE", "v2_shadow")
    status = guard_admin_status(DEMO_AGENT_ID)
    components = {
        component.component_id: component
        for component in status.components
    }

    assert status.active_enforcement == "firewall_v1"
    assert status.policy.status == "operational"
    assert status.policy.editable is True
    assert status.policy.version == resolve_demo_policy().document.version
    assert status.policy.effective_hash.startswith("sha256:")
    assert components["tool_descriptors"].status == "operational"
    assert components["v2_shadow"].status == "observe_only"
    assert components["policy_engine"].status == "operational"
    assert components["normalization"].status == "operational"
    assert "Gmail and future MCP normalizers are not implemented yet" in (
        components["normalization"].summary
    )
    assert components["intent_contract"].status == "not_implemented"
    assert components["tier_1"].status == "operational"


def test_personal_assistant_policy_loads_with_expected_scope():
    loaded = resolve_demo_policy()

    assert loaded.document.policy_id == "pol_personal_assistant"
    assert len(loaded.document.version.split(".")) == 3
    assert loaded.document.status == "published"
    assert loaded.document.scope.workspace_id == DEMO_WORKSPACE_ID
    assert loaded.document.scope.agent_id == DEMO_AGENT_ID
    assert loaded.document.scope.deployment_id == DEMO_DEPLOYMENT_ID
    assert loaded.effective_hash.startswith("sha256:")


def test_policy_api_contract_returns_real_document_and_validates_candidates():
    registry = DemoAgentRegistry()
    active = get_agent_policy(DEMO_AGENT_ID, registry)
    candidate = active.document.copy()
    major, minor, patch = (int(part) for part in active.version.split("."))
    candidate["version"] = f"{major}.{minor}.{patch + 1}"

    validation = validate_agent_policy(
        DEMO_AGENT_ID,
        PolicyValidationRequest(document=candidate),
        registry,
    )

    assert active.policy_id == "pol_personal_assistant"
    assert active.validation == "valid"
    assert active.document["rules"]
    assert validation.valid is True
    assert validation.version == candidate["version"]
    assert validation.effective_hash != active.effective_hash


def test_policy_api_validation_rejects_candidate_for_another_agent():
    registry = DemoAgentRegistry()
    candidate = resolve_demo_policy().document.model_dump(mode="json")
    candidate["scope"]["agent_id"] = "agt_other"

    validation = validate_agent_policy(
        DEMO_AGENT_ID,
        PolicyValidationRequest(document=candidate),
        registry,
    )

    assert validation.valid is False
    assert validation.errors


def test_policy_api_validation_rejects_unknown_fields():
    registry = DemoAgentRegistry()
    candidate = resolve_demo_policy().document.model_dump(mode="json")
    candidate["rules"][0]["match"]["capabilites_any"] = ["filesystem.delete"]

    validation = validate_agent_policy(
        DEMO_AGENT_ID,
        PolicyValidationRequest(document=candidate),
        registry,
    )

    assert validation.valid is False
    assert "Extra inputs are not permitted" in validation.errors[0]


def test_policy_api_publishes_next_version_and_rejects_stale_write(
    monkeypatch,
    tmp_path,
):
    source = resolve_demo_policy()
    source_version = source.document.version
    policy_path = tmp_path / "active_policy.json"
    policy_path.write_text(source.raw_text, encoding="utf-8")
    monkeypatch.setenv("AGENTGUARD_POLICY_PATH", str(policy_path))
    registry = DemoAgentRegistry()
    active = get_agent_policy(DEMO_AGENT_ID, registry)
    candidate = active.document.copy()
    candidate["description"] = "Updated from the Guard Admin test."

    updated = update_agent_policy(
        DEMO_AGENT_ID,
        PolicyUpdateRequest(
            expected_hash=active.effective_hash,
            document=candidate,
        ),
        registry,
    )

    major, minor, patch = (int(part) for part in source_version.split("."))
    next_version = f"{major}.{minor}.{patch + 1}"
    assert updated.version == next_version
    assert updated.effective_hash != active.effective_hash
    assert updated.document["description"] == "Updated from the Guard Admin test."
    assert json.loads(policy_path.read_text(encoding="utf-8"))["version"] == next_version

    with pytest.raises(HTTPException) as error:
        update_agent_policy(
            DEMO_AGENT_ID,
            PolicyUpdateRequest(
                expected_hash=active.effective_hash,
                document=candidate,
            ),
            registry,
        )
    assert error.value.status_code == 409


def test_policy_loader_rejects_wrong_agent_scope(tmp_path):
    source = resolve_demo_policy()
    payload = source.document.model_dump(mode="json")
    payload["scope"]["agent_id"] = "agt_wrong"
    path = tmp_path / "wrong_scope.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PolicyValidationError, match="does not match"):
        PolicyLoader(default_path=path).load(
            workspace_id=DEMO_WORKSPACE_ID,
            agent_id=DEMO_AGENT_ID,
            deployment_id=DEMO_DEPLOYMENT_ID,
        )


def test_policy_document_rejects_duplicate_rule_ids():
    payload = resolve_demo_policy().document.model_dump(mode="json")
    payload["rules"].append(dict(payload["rules"][0]))

    with pytest.raises(ValueError, match="unique"):
        PolicyDocumentV1.model_validate(payload)


def test_policy_hash_changes_when_document_changes(tmp_path):
    source = resolve_demo_policy()
    payload = source.document.model_dump(mode="json")
    payload["version"] = "1.0.1"
    payload["defaults"]["no_rule_match"] = "block"
    path = tmp_path / "changed_policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    changed = PolicyLoader(default_path=path).load(
        workspace_id=DEMO_WORKSPACE_ID,
        agent_id=DEMO_AGENT_ID,
        deployment_id=DEMO_DEPLOYMENT_ID,
    )

    assert changed.document.version == "1.0.1"
    assert changed.effective_hash != source.effective_hash


def test_personal_assistant_policy_capability_recommendations():
    evaluator = PolicyEvaluatorV1(resolve_demo_policy())

    shell = evaluator.evaluate(descriptor_for_tool("run_shell_command"))
    search = evaluator.evaluate(descriptor_for_tool("gmail_search"))
    draft = evaluator.evaluate(descriptor_for_tool("gmail_draft"))
    send = evaluator.evaluate(descriptor_for_tool("gmail_send_email"))
    unknown = evaluator.evaluate(descriptor_for_tool("custom_payment_tool"))
    destructive = evaluator.evaluate(
        ToolDescriptorV1(
            tool_name="drive_delete",
            provider="google_workspace",
            category="drive",
            capabilities=["drive.delete"],
            impact="high",
            reversible=False,
            normalizer="drive_v1",
            metadata_status="built_in",
        )
    )
    payment = evaluator.evaluate(
        ToolDescriptorV1(
            tool_name="wallet_transfer",
            provider="payment_mcp",
            category="payment",
            capabilities=["payment.execute"],
            impact="high",
            reversible=False,
            normalizer="payment_v1",
            metadata_status="built_in",
        )
    )

    assert shell.recommendation == "require_approval"
    assert search.recommendation == "allow"
    assert draft.recommendation == "allow"
    assert send.recommendation == "require_approval"
    assert "approve_untrusted_email_destinations" in send.deferred_rule_ids
    assert unknown.recommendation == "block"
    assert destructive.recommendation == "block"
    assert payment.recommendation == "block"


@pytest.mark.parametrize(
    ("command", "operation", "capability", "status"),
    [
        ("pwd", "inspect", "filesystem.inspect", "parsed"),
        ("cat README.md", "read", "filesystem.read", "parsed"),
        ("touch notes.txt", "write", "filesystem.write", "parsed"),
        ("rm notes.txt", "delete", "filesystem.delete", "parsed"),
        ("curl https://example.com", "network_request", "shell.network_request", "parsed"),
        ("sudo whoami", "privilege_escalation", "system.privilege_escalate", "parsed"),
        ("echo hello > notes.txt", "write", "filesystem.write", "partial"),
        ("echo hello | tee notes.txt", "unknown", "unknown", "unsupported"),
        ("echo $(whoami)", "unknown", "unknown", "unsupported"),
        ("custom-command value", "unknown", "unknown", "unsupported"),
    ],
)
def test_shell_normalizer_classifies_supported_and_unknown_commands(
    tmp_path,
    command,
    operation,
    capability,
    status,
):
    session = _trace_session(tmp_path)
    session.start_turn(f"Run this command: {command}")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": command},
        call_id=f"call_{abs(hash(command))}",
    )

    action = ShellNormalizerV1().normalize(result.trace)

    assert action.operation == operation
    assert action.capabilities == [capability]
    assert action.parser.status == status
    if status == "unsupported":
        assert action.parser.confidence < 0.5
        assert "unknown_or_unsupported" in action.flags


def test_shell_normalizer_marks_sensitive_path_and_policy_blocks_it(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Read my SSH private key.")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": "cat ~/.ssh/id_rsa"},
        call_id="call_sensitive",
    )

    action = ShellNormalizerV1().normalize(result.trace)
    evaluation = PolicyEvaluatorV1(resolve_demo_policy()).evaluate(
        descriptor_for_tool("run_shell_command"),
        action=action,
    )

    assert action.capabilities == ["filesystem.read"]
    assert action.resources[0].sensitivity == "sensitive"
    assert "sensitive_path_access" in action.flags
    assert evaluation.recommendation == "block"
    assert "protect_sensitive_paths" in {
        match.rule_id for match in evaluation.matched_rules
    }


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("pwd", "allow"),
        ("cat README.md", "allow"),
        ("touch notes.txt", "require_approval"),
        ("rm notes.txt", "block"),
        ("curl https://example.com", "block"),
        ("sudo whoami", "block"),
        ("echo hello | tee notes.txt", "require_approval"),
    ],
)
def test_shell_normalized_policy_recommendations(tmp_path, command, expected):
    session = _trace_session(tmp_path)
    session.start_turn(f"Run this command: {command}")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": command},
        call_id=f"call_policy_{abs(hash(command))}",
    )
    action = ShellNormalizerV1().normalize(result.trace)

    evaluation = PolicyEvaluatorV1(resolve_demo_policy()).evaluate(
        descriptor_for_tool("run_shell_command"),
        action=action,
    )

    assert evaluation.recommendation == expected


def test_shell_redirection_records_written_resource(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Create notes.txt containing hello.")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": "echo hello > notes.txt"},
        call_id="call_redirect",
    )

    action = ShellNormalizerV1().normalize(result.trace)

    assert action.operation == "write"
    assert "redirection" in action.flags
    assert [resource.value for resource in action.resources] == ["notes.txt"]
    assert action.resources[0].access == "write"


def test_policy_uses_most_restrictive_matching_effect(tmp_path):
    payload = resolve_demo_policy().document.model_dump(mode="json")
    payload["version"] = "1.1.0"
    payload["rules"].append(
        {
            "rule_id": "block_email_send_test",
            "description": "Test stricter email rule.",
            "effect": "block",
            "severity": "critical",
            "non_overridable": False,
            "match": {
                "capabilities_any": ["email.send"],
                "tools_any": [],
                "resource_constraints": {},
            },
        }
    )
    path = tmp_path / "strict_policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = PolicyLoader(default_path=path).load(
        workspace_id=DEMO_WORKSPACE_ID,
        agent_id=DEMO_AGENT_ID,
        deployment_id=DEMO_DEPLOYMENT_ID,
    )

    evaluation = PolicyEvaluatorV1(loaded).evaluate(
        descriptor_for_tool("gmail_send_email")
    )

    assert evaluation.recommendation == "block"
    assert {item.effect for item in evaluation.matched_rules} == {
        "require_approval",
        "block",
    }


def test_before_tool_callback_blocks_forbidden_call(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="workspace_gmail_send"),
        {"to": "finance@example.com", "body": "Draft body"},
        _fake_tool_context("Draft a reply but do not send it."),
    )

    assert response is not None
    assert response["approval_required"] is True
    assert response["blocked_by_agentguard"] is True
    assert response["runtime_policy"] == "require_approval"
    assert response["firewall_decision"] == "require_approval"


def test_before_tool_callback_allows_approval_when_enforcement_disabled(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "false")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="workspace_gmail_send"),
        {"to": "finance@example.com", "body": "Draft body"},
        _fake_tool_context("Draft a reply but do not send it."),
    )

    assert response is None


def test_before_tool_callback_enforces_v2_destructive_shell_block(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("ADK_GMAIL_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_FIREWALL_MODE", "v2")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "rm v2-callback-test.txt"},
        _fake_tool_context("Delete v2-callback-test.txt."),
    )

    assert response is not None
    assert response["blocked_by_agentguard"] is True
    assert response["runtime_policy"] == "block"
    assert response["firewall_decision"] == "block"
    events = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl"
    )
    v2_payload = next(
        event["payload"]
        for event in events
        if event["event_type"] == "firewall_v2_evaluated"
    )
    assert v2_payload["enforced_by"] == "firewall_v2"
    assert v2_payload["enforced_decision"] == "block"


def test_before_tool_callback_force_blocks_every_tool_call(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "false")
    monkeypatch.setenv("AGENTGUARD_FORCE_BLOCK", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "touch should-not-exist"},
        _fake_tool_context("Create a file."),
    )

    assert response is not None
    assert response["approval_required"] is False
    assert response["blocked_by_agentguard"] is True
    assert response["runtime_policy"] == "block"
    assert response["firewall_decision"] == "block"

    decisions = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk" / "decisions.jsonl"
    )
    assert decisions[0]["decision"] == "block"
    assert decisions[0]["decision_rules_fired"] == ["force_block_enabled"]
    assert "force_block_enabled" in decisions[0]["explanation"]

    blocked_events = [
        event
        for event in load_jsonl(
            tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl"
        )
        if event["event_type"] == "tool_blocked"
    ]
    assert len(blocked_events) == 1
    assert blocked_events[0]["payload"]["runtime_event_source"] == "google_adk_adapter"
    assert blocked_events[0]["payload"]["runtime_policy"] == "block"
    assert blocked_events[0]["payload"]["approval_required"] is False


def test_google_adk_trace_session_records_v2_shadow_evidence(tmp_path):
    session = _trace_session(tmp_path, firewall_mode="v2_shadow")
    session.start_turn("Show me the current directory.")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_shell",
    )

    events = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk_test" / "live_events.jsonl"
    )
    v2_events = [
        event for event in events if event["event_type"] == "firewall_v2_evaluated"
    ]
    assert len(v2_events) == 1
    payload = v2_events[0]["payload"]
    assert payload["runtime_event_source"] == "google_adk_adapter"
    assert payload["enforced_by"] == "firewall_v1"
    assert payload["enforced_decision"] == result.decision.decision
    assert payload["firewall_mode"] == "v2_shadow"
    assert payload["evaluation"]["enforcement_status"] == "observe_only"
    assert payload["evaluation"]["tool_descriptor"]["tool_name"] == "run_shell_command"
    assert payload["evaluation"]["stages"][1]["name"] == "policy"
    assert payload["evaluation"]["stages"][1]["status"] == "completed"
    assert payload["evaluation"]["policy_evaluation"]["policy_id"] == (
        "pol_personal_assistant"
    )
    assert payload["evaluation"]["normalized_action"]["operation"] == "inspect"
    assert payload["evaluation"]["stages"][2]["status"] == "completed"
    assert payload["evaluation"]["policy_evaluation"]["recommendation"] == "allow"


def test_running_v2_session_reloads_policy_after_publish(monkeypatch, tmp_path):
    source = resolve_demo_policy()
    source_version = source.document.version
    policy_path = tmp_path / "reloadable_policy.json"
    policy_path.write_text(source.raw_text, encoding="utf-8")
    monkeypatch.setenv("AGENTGUARD_POLICY_PATH", str(policy_path))
    session = _trace_session(tmp_path, firewall_mode="v2_shadow")
    session.start_turn("Show me the current directory twice.")
    session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_before_policy_update",
    )

    loaded = resolve_demo_policy()
    candidate = loaded.document.model_dump(mode="json")
    retrieval_rule = next(
        rule
        for rule in candidate["rules"]
        if rule["rule_id"] == "allow_information_retrieval"
    )
    retrieval_rule["effect"] = "block"
    PolicyStore().publish(candidate, expected_hash=loaded.effective_hash)

    session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_after_policy_update",
    )

    events = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk_test" / "live_events.jsonl"
    )
    recommendations = [
        event["payload"]["evaluation"]["policy_evaluation"]["recommendation"]
        for event in events
        if event["event_type"] == "firewall_v2_evaluated"
    ]
    versions = [
        event["payload"]["evaluation"]["policy_evaluation"]["policy_version"]
        for event in events
        if event["event_type"] == "firewall_v2_evaluated"
    ]
    assert recommendations == ["allow", "block"]
    major, minor, patch = (int(part) for part in source_version.split("."))
    assert versions == [source_version, f"{major}.{minor}.{patch + 1}"]


def test_google_adk_trace_session_v2_mode_enforces_allow(tmp_path):
    session = _trace_session(tmp_path, firewall_mode="v2")
    session.start_turn("Show me the current directory.")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_shell",
    )

    events = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk_test" / "live_events.jsonl"
    )
    payload = next(
        event["payload"]
        for event in events
        if event["event_type"] == "firewall_v2_evaluated"
    )
    assert result.decision.decision == "allow"
    assert result.decision.tier_used == "static_policy"
    assert payload["enforced_by"] == "firewall_v2"
    assert payload["enforced_decision"] == "allow"
    assert payload["evaluation"]["enforcement_status"] == "enforced"
    assert payload["effective_decision"]["decision"] == "allow"


@pytest.mark.parametrize(
    ("command", "expected_decision"),
    [
        ("touch v2-policy-test.txt", "require_approval"),
        ("rm v2-policy-test.txt", "block"),
        ("curl https://example.com", "block"),
        ("unknown_agentguard_command", "require_approval"),
    ],
)
def test_google_adk_trace_session_v2_mode_enforces_policy_recommendation(
    tmp_path,
    command,
    expected_decision,
):
    session = _trace_session(tmp_path, firewall_mode="v2")
    session.start_turn(f"Run: {command}")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": command},
        call_id=f"call_{expected_decision}",
    )

    assert result.decision.decision == expected_decision
    assert adk_runtime_policy(result.decision.decision) == (
        "allow" if expected_decision == "allow" else expected_decision
    )
    assert result.decision.explanation.startswith("FirewallV2 enforced")


def test_v2_mode_keeps_force_block_as_emergency_override(tmp_path):
    session = GoogleADKTraceSession(
        session_id="force_block_v2_session",
        agent_id="terminal_assistant",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        available_tools=["run_shell_command"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="google_adk_test",
        firewall_mode="v2",
        force_block=True,
    )
    session.start_turn("Show me the current directory.")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": "pwd"},
        call_id="call_force_block_v2",
    )

    events = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk_test" / "live_events.jsonl"
    )
    payload = next(
        event["payload"]
        for event in events
        if event["event_type"] == "firewall_v2_evaluated"
    )
    assert result.decision.decision == "block"
    assert payload["enforced_by"] == "emergency_force_block"
    assert payload["evaluation"]["policy_evaluation"]["recommendation"] == "allow"


def test_dashboard_query_uses_v2_effective_decision_for_replay(tmp_path):
    session = _trace_session(tmp_path, firewall_mode="v2")
    session.start_turn("Delete the temporary file.")
    result = session.record_tool_call(
        "run_shell_command",
        {"command": "rm v2-policy-test.txt"},
        call_id="call_block",
    )
    session.record_tool_response(
        "run_shell_command",
        {"blocked_by_agentguard": True, "runtime_policy": "block"},
        call_id="call_block",
    )

    service = DashboardQueryService(
        LocalDashboardRepository(
            root=tmp_path / "traces",
            namespace="google_adk_test",
        )
    )
    replay = service.session(result.trace.session_id, agent_id=result.trace.source.agent_id)

    assert replay is not None
    assert replay.session.final_decision == "block"
    assert replay.steps[0].decision == "block"
    assert replay.steps[0].rules_fired == ["block_destructive_actions"]
    assert replay.steps[0].explanation.startswith("FirewallV2 enforced block")


def test_google_adk_trace_session_records_tool_executed_event(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    result = session.record_tool_call(
        "workspace_gmail_search", {"query": "budget"}, call_id="call_search"
    )

    session.record_tool_response(
        "workspace_gmail_search",
        {"results": ["thread_budget_q2"]},
        call_id="call_search",
    )

    runtime_events = _runtime_events(tmp_path)
    executed_events = [event for event in runtime_events if event["event_type"] == "tool_executed"]
    assert adk_runtime_policy(result.decision.decision) == "allow"
    assert len(executed_events) == 1
    assert executed_events[0]["payload"]["execution_status"] == "executed"
    assert executed_events[0]["payload"]["runtime_policy"] == "allow"
    assert executed_events[0]["payload"]["firewall_decision"] == result.decision.decision


def test_google_adk_trace_uses_adk_tool_metadata(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")

    result = session.record_tool_call(
        "workspace_gmail_search", {"query": "budget"}, call_id="call_search"
    )

    tool = result.trace.proposed_tool_call
    assert tool.tool_category == "email"
    assert tool.risk_level == "read_only"
    assert tool.side_effect_type is None
    assert tool.mcp_server == "workspace"


def test_google_adk_shell_trace_uses_shell_metadata(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Show me the current directory.")

    result = session.record_tool_call("run_shell_command", {"command": "pwd"}, call_id="call_shell")

    tool = result.trace.proposed_tool_call
    assert result.trace.intent.domain == "shell"
    assert tool.tool_category == "shell"
    assert tool.risk_level == "low_side_effect"
    assert tool.side_effect_type == "shell_command"
    assert tool.mcp_server is None


def test_runtime_event_references_persisted_decision(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("workspace_gmail_search", {"query": "budget"}, call_id="call_search")

    session.record_tool_response(
        "workspace_gmail_search",
        {"results": ["thread_budget_q2"]},
        call_id="call_search",
    )

    decisions = load_jsonl(tmp_path / "traces" / "v1" / "google_adk_test" / "decisions.jsonl")
    decision_ids = {decision["decision_id"] for decision in decisions}
    executed_events = [event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_executed"]
    assert executed_events[0]["payload"]["decision_id"] in decision_ids


def test_google_adk_trace_session_records_tool_failed_event(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("workspace_gmail_search", {"query": "budget"}, call_id="call_search")

    session.record_tool_response(
        "workspace_gmail_search",
        {"error": "MCP server unavailable"},
        call_id="call_search",
    )

    failed_events = [
        event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_failed"
    ]
    assert len(failed_events) == 1
    assert failed_events[0]["payload"]["execution_status"] == "failed"
    assert failed_events[0]["payload"]["runtime_event_source"] == "google_adk_adapter"


def test_record_tool_response_is_idempotent_for_same_call_id(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("workspace_gmail_search", {"query": "budget"}, call_id="call_search")

    session.record_tool_response(
        "workspace_gmail_search", {"results": ["thread_budget_q2"]}, call_id="call_search"
    )
    session.record_tool_response(
        "workspace_gmail_search", {"results": ["thread_budget_q2"]}, call_id="call_search"
    )

    executed_events = [event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_executed"]
    assert len(executed_events) == 1


def test_record_tool_response_matches_without_call_id(tmp_path):
    session = _trace_session(tmp_path)
    session.start_turn("Search my inbox for the latest budget thread.")
    session.record_tool_call("workspace_gmail_search", {"query": "budget"}, call_id=None)

    session.record_tool_response("workspace_gmail_search", {"results": ["thread_budget_q2"]}, call_id=None)

    executed_events = [event for event in _runtime_events(tmp_path) if event["event_type"] == "tool_executed"]
    assert len(executed_events) == 1
    assert executed_events[0]["payload"]["execution_status"] == "executed"


def test_before_tool_callback_allows_normal_shell_command(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "pwd"},
        _fake_tool_context("Show me the current directory."),
    )

    assert response is None


def test_adk_elastic_override_can_disable_global_elastic(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTGUARD_ELASTIC_ENABLED", "true")
    monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
    monkeypatch.delenv("ELASTICSEARCH_API_KEY", raising=False)
    monkeypatch.setenv("AGENTGUARD_ADK_ELASTIC_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    response = adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "pwd"},
        _fake_tool_context("Show me the current directory."),
    )

    assert response is None


def test_before_tool_callback_records_approval_blocked_runtime_event(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTGUARD_ADK_ENFORCE_APPROVAL", "true")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    adk_agent._before_tool_callback(
        SimpleNamespace(name="workspace_gmail_send"),
        {"to": "finance@example.com", "body": "Draft body"},
        _fake_tool_context("Draft a reply but do not send it."),
    )

    blocked_events = [
        event
        for event in load_jsonl(
            tmp_path / "traces" / "v1" / "google_adk" / "live_events.jsonl"
        )
        if event["event_type"] == "tool_blocked"
        and event["payload"].get("runtime_event_source") == "google_adk_adapter"
    ]
    assert len(blocked_events) == 1
    assert blocked_events[0]["payload"]["execution_status"] == "blocked"
    assert blocked_events[0]["payload"]["approval_required"] is True
    assert blocked_events[0]["payload"]["runtime_policy"] == "require_approval"


def test_adk_callback_uses_registered_dashboard_agent_identity(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTGUARD_ADK_ELASTIC_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_TRACE_ROOT", str(tmp_path / "traces"))
    adk_agent = _load_adk_agent()
    adk_agent._TRACE_SESSIONS.clear()

    adk_agent._before_tool_callback(
        SimpleNamespace(name="run_shell_command"),
        {"command": "pwd"},
        _fake_tool_context("Show me the current directory."),
    )

    trace = load_jsonl(
        tmp_path / "traces" / "v1" / "google_adk" / "traces.jsonl"
    )[0]
    assert trace["source"]["workspace_id"] == DEMO_WORKSPACE_ID
    assert trace["source"]["agent_id"] == DEMO_AGENT_ID
    assert trace["source"]["deployment_id"] == DEMO_DEPLOYMENT_ID
    assert trace["source"]["integration_id"] == DEMO_INTEGRATION_ID


def _fake_tool_context(user_text: str):
    return SimpleNamespace(
        session=SimpleNamespace(id="adk_callback_session"),
        invocation_id="adk_callback_invocation",
        agent_name="terminal_assistant",
        user_content=SimpleNamespace(parts=[SimpleNamespace(text=user_text)]),
        function_call_id="call_001",
    )


def _load_adk_agent():
    pytest.importorskip("google.adk", reason="google-adk is an optional runtime dependency")
    module = importlib.import_module("apps.adk_agent.agent")
    return importlib.reload(module)


def _trace_session(tmp_path, firewall_mode="v1"):
    return GoogleADKTraceSession(
        session_id="adk_test_session",
        agent_id="terminal_assistant",
        runtime_agent_id="terminal_assistant",
        agent_config_id="adk_terminal_assistant",
        available_tools=["run_shell_command", "workspace_gmail_search", "workspace_gmail_send"],
        trace_store=TraceStore(root_dir=tmp_path / "traces"),
        namespace="google_adk_test",
        metadata_resolver=_mcp_registry().metadata_for,
        firewall_mode=firewall_mode,
    )


def _mcp_registry():
    return McpRegistry.load("config/adk_mcp_servers.toml")


def _runtime_events(tmp_path):
    return [
        event
        for event in load_jsonl(
            tmp_path / "traces" / "v1" / "google_adk_test" / "live_events.jsonl"
        )
        if event["payload"].get("runtime_event_source") == "google_adk_adapter"
    ]
