"""Production remote interception service backed by FirewallV2."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from agentguard.control_plane.models import RegisteredTool
from agentguard.control_plane.registry import AgentRegistry
from agentguard.core.models import ExecutedToolCall
from agentguard.firewall_v2.config import FirewallV2RuntimeConfig
from agentguard.firewall_v2.engine import AgentGuardFirewallV2
from agentguard.firewall_v2.models import FirewallV2Evaluation
from agentguard.firewall_v2.tools.metadata_inference import infer_registered_tool_metadata
from agentguard.firewall_v2.tools.registry import descriptor_for_tool
from agentguard.intent.extractor import IntentExtractor
from agentguard.intent.models import IntentContractV2
from agentguard.runtime.tool_registry import ToolMetadata
from agentguard.server.models import (
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    ApprovalListResponse,
    ApprovalRequest,
    EnforcementDecisionResponse,
    EventEnvelope,
    OutcomeReportRequest,
    OutcomeReportResponse,
    PendingApproval,
    ToolProposalRequest,
    TurnStartRequest,
    TurnStartResponse,
)
from agentguard.server.services.query import guard_evaluation_from_payload
from agentguard.server.services.live import EventBroker
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    ComponentScoresV1,
    CumulativeScoresV1,
    DecisionThresholdsV1,
    GuardDecisionV1,
    GuardScoreV1,
    LiveEventV1,
    RetrievalFeatureV1,
    TraceFeatureV1,
    TraceSourceV1,
)
from agentguard.tracing.serializers import append_jsonl, load_jsonl
from agentguard.tracing.trace_store import TraceStore
from agentguard.tracing.trace_v1_builder import TraceV1BuildInput, TraceV1Builder


class RemoteInterceptionService:
    def __init__(
        self,
        *,
        registry: AgentRegistry,
        trace_store: TraceStore,
        namespace: str = "registered_agents",
        approval_root: Path | str = "data/approvals",
    ):
        self.registry = registry
        self.trace_store = trace_store
        self.namespace = namespace
        self.approval_root = Path(approval_root)
        self.broker = EventBroker()
        self._builder = TraceV1Builder()
        self._intent_extractor = IntentExtractor(
            llm_enabled=FirewallV2RuntimeConfig.from_env().intent_llm_enabled
        )
        self._intent_by_id: dict[str, IntentContractV2] = {}
        self._turn_request_by_id: dict[str, TurnStartRequest] = {}
        self._pending_by_id: dict[str, PendingApproval] = self._load_approvals()
        self._decision_by_id: dict[str, tuple[AgentGuardTraceV1, EnforcementDecisionResponse]] = {}
        self._prior_calls_by_session: dict[str, list[ExecutedToolCall]] = defaultdict(list)
        self._previous_trace_by_session: dict[str, str] = {}
        self._previous_output_by_session: dict[str, str] = {}
        self._hydrate_runtime_state()

    def register(
        self,
        request: AgentRegistrationRequest,
    ) -> AgentRegistrationResponse:
        self.registry.register(request)
        return AgentRegistrationResponse(
            agent_id=request.agent_id,
            workspace_id=request.workspace_id,
        )

    async def start_turn(self, request: TurnStartRequest) -> TurnStartResponse:
        definition = self._definition(request.agent_id)
        descriptors = [
            descriptor_for_tool(tool.name, self._metadata(tool))
            for tool in definition.tools
        ]
        contract = self._intent_extractor.extract(
            user_request=request.user_request,
            session_id=request.session_id,
            agent_id=request.agent_id,
            turn_id=request.turn_id,
            tool_descriptors=descriptors,
        )
        self._intent_by_id[contract.intent_id] = contract
        self._turn_request_by_id[request.turn_id] = request
        self.trace_store.append_intent_contract_v2(contract, namespace=self.namespace)
        await self._publish(
            "turn_started",
            {
                "workspace_id": request.workspace_id,
                "agent_id": request.agent_id,
                "session_id": request.session_id,
                "turn_id": request.turn_id,
                "intent_id": contract.intent_id,
                "intent_contract": contract.model_dump(mode="json"),
            },
        )
        return TurnStartResponse(intent_id=contract.intent_id, turn_id=request.turn_id)

    async def evaluate(
        self,
        request: ToolProposalRequest,
    ) -> EnforcementDecisionResponse:
        started = perf_counter()
        definition = self._definition(request.agent_id)
        tool = self._tool(definition.tools, request.tool_name)
        metadata = self._metadata(tool)
        trace = self._build_trace(request, metadata)
        self.trace_store.append_trace_v1(trace, namespace=self.namespace)
        await self._record_event("tool_proposed", trace, {"proposal": request.model_dump(mode="json")})

        config = FirewallV2RuntimeConfig.from_env().model_copy(
            update={
                "tier_1_enabled": True,
                "tier_2_enabled": False,
                "tier_3_enabled": True,
                "tier_3_enforcement_enabled": True,
                "mock_pipeline_only": False,
            }
        )
        evaluation = AgentGuardFirewallV2(
            mode="v2",
            runtime_config=config,
            descriptor_resolver=lambda tool_name: descriptor_for_tool(tool_name, metadata),
        ).evaluate(trace, self._intent_by_id.get(request.intent_id))
        decision = self._decision_from_evaluation(
            request=request,
            trace=trace,
            evaluation=evaluation,
            latency_ms=int((perf_counter() - started) * 1000),
        )
        self.trace_store.append_feature_v1(
            _feature_from_evaluation(trace, evaluation),
            namespace=self.namespace,
        )
        self.trace_store.append_score_v1(
            _score_from_decision(trace, decision),
            namespace=self.namespace,
        )
        self.trace_store.append_decision_v1(decision, namespace=self.namespace)
        await self._record_event(
            "firewall_v2_evaluated",
            trace,
            {
                "runtime_event_source": "remote_agentguard_api",
                "enforced_by": (
                    (evaluation.combined_decision or {}).get("enforced_by")
                    or "firewall_v2"
                ),
                "enforced_decision": decision.decision,
                "effective_decision": decision.model_dump(mode="json", by_alias=True),
                "firewall_mode": "v2",
                "evaluation": evaluation.model_dump(mode="json", by_alias=True),
            },
        )
        approval_id = None
        if decision.decision == "require_approval":
            approval_id = await self._create_approval(request, trace, decision, evaluation)
        response = EnforcementDecisionResponse(
            decision_id=decision.decision_id,
            trace_id=trace.trace_id,
            call_id=request.call_id,
            decision=decision.decision,
            explanation=decision.explanation,
            policy_id=(evaluation.policy_evaluation or {}).get("policy_id"),
            policy_version=(evaluation.policy_evaluation or {}).get("policy_version"),
            policy_hash=(evaluation.policy_evaluation or {}).get("policy_hash"),
            matched_rules=list((evaluation.policy_evaluation or {}).get("matched_rules") or []),
            normalized_action=evaluation.normalized_action,
            tier_evidence=evaluation.tier_results,
            approval_request_id=approval_id,
            evaluation_latency_ms=decision.latency_ms,
        )
        self._decision_by_id[decision.decision_id] = (trace, response)
        return response

    def list_approvals(self, status: str | None = "pending") -> ApprovalListResponse:
        items = sorted(
            self._pending_by_id.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        if status:
            items = [item for item in items if item.status == status]
        return ApprovalListResponse(items=items)

    def get_approval(self, approval_id: str) -> PendingApproval:
        approval = self._pending_by_id.get(approval_id)
        if approval is None:
            raise KeyError(approval_id)
        return approval

    async def resolve_approval(
        self,
        approval_id: str,
        request: ApprovalRequest,
        action: str,
    ) -> PendingApproval:
        approval = self.get_approval(approval_id)
        if approval.status != "pending":
            return approval
        status = {
            "approve": "approved",
            "reject": "rejected",
            "abort": "aborted",
        }[action]
        approval = approval.model_copy(
            update={
                "status": status,
                "resolved_at": datetime.now(timezone.utc),
                "resolved_by": request.actor,
                "note": request.note,
            }
        )
        self._pending_by_id[approval_id] = approval
        append_jsonl(self._approvals_path, approval)
        await self._publish("approval.resolved", approval.model_dump(mode="json"))
        return approval

    async def report_outcome(
        self,
        request: OutcomeReportRequest,
    ) -> OutcomeReportResponse:
        pending = self._decision_by_id.get(request.decision_id)
        if pending is None:
            return OutcomeReportResponse()
        trace, _decision = pending
        status = {
            "executed": "executed",
            "failed": "failed",
            "blocked": "blocked",
            "cancelled": "blocked",
        }.get(request.status, "blocked")
        if status in {"executed", "failed"}:
            self._prior_calls_by_session[trace.session_id].append(
                ExecutedToolCall(
                    call_id=trace.proposed_tool_call.call_id,
                    session_id=trace.session_id,
                    step_index=trace.step_index,
                    tool_name=trace.proposed_tool_call.tool_name,
                    arguments=trace.proposed_tool_call.arguments,
                    output_summary=request.output_summary,
                    status=status,
                )
            )
            self._previous_trace_by_session[trace.session_id] = trace.trace_id
            self._previous_output_by_session[trace.session_id] = request.output_summary or ""
        event_type = {
            "executed": "tool_executed",
            "failed": "tool_failed",
        }.get(status, "tool_blocked")
        await self._record_event(
            event_type,
            trace,
            {
                "execution_status": status,
                "output_summary": request.output_summary,
                "latency_ms": request.latency_ms,
                "error_type": request.error_type,
                "error_message": request.error_message,
            },
        )
        return OutcomeReportResponse()

    @property
    def _approvals_path(self) -> Path:
        return self.approval_root / "approvals.jsonl"

    def _load_approvals(self) -> dict[str, PendingApproval]:
        latest: dict[str, PendingApproval] = {}
        for record in load_jsonl(self._approvals_path):
            approval = PendingApproval.model_validate(record)
            latest[approval.approval_id] = approval
        return latest

    def _hydrate_runtime_state(self) -> None:
        for contract in self.trace_store.load_intent_contracts_v2(
            namespace=self.namespace
        ):
            self._intent_by_id[contract.intent_id] = contract

        output_by_trace: dict[str, tuple[str, str]] = {}
        for event in self.trace_store.load_live_events_v1(namespace=self.namespace):
            if event.trace_id is None or event.event_type not in {
                "tool_executed",
                "tool_blocked",
                "tool_failed",
            }:
                continue
            output_by_trace[event.trace_id] = (
                str(event.payload.get("execution_status") or "blocked"),
                str(event.payload.get("output_summary") or ""),
            )

        traces = sorted(
            self.trace_store.load_traces_v1(namespace=self.namespace),
            key=lambda trace: trace.timestamp,
        )
        for trace in traces:
            self._previous_trace_by_session[trace.session_id] = trace.trace_id
            status, output = output_by_trace.get(
                trace.trace_id,
                (trace.execution.status, trace.execution.output_summary or ""),
            )
            if output:
                self._previous_output_by_session[trace.session_id] = output
            self._prior_calls_by_session[trace.session_id].append(
                ExecutedToolCall(
                    call_id=trace.proposed_tool_call.call_id,
                    session_id=trace.session_id,
                    step_index=trace.step_index,
                    tool_name=trace.proposed_tool_call.tool_name,
                    arguments=trace.proposed_tool_call.arguments,
                    output_summary=output,
                    status=_executed_status(status),
                )
            )

    def _definition(self, agent_id: str):
        definition = self.registry.definition(agent_id)
        if definition is None:
            raise KeyError(agent_id)
        return definition

    @staticmethod
    def _tool(tools: list[RegisteredTool], name: str) -> RegisteredTool:
        for tool in tools:
            if tool.name == name or tool.source_name == name:
                return tool
        raise KeyError(name)

    @staticmethod
    def _metadata(tool: RegisteredTool) -> ToolMetadata:
        return infer_registered_tool_metadata(tool)

    def _build_trace(
        self,
        request: ToolProposalRequest,
        metadata: ToolMetadata,
    ) -> AgentGuardTraceV1:
        turn = self._turn_request_by_id.get(request.turn_id)
        intent_contract = self._intent_by_id.get(request.intent_id)
        user_request = (
            turn.user_request
            if turn is not None
            else intent_contract.raw_user_request
            if intent_contract is not None
            else "User request unavailable."
        )
        return self._builder.build(
            TraceV1BuildInput(
                session_id=request.session_id,
                step_index=len(self._prior_calls_by_session[request.session_id]) + 1,
                source=TraceSourceV1(
                    mode="live",
                    agent_framework="google_adk",
                    source_type="remote_sdk",
                    agent_id=request.agent_id,
                    workspace_id=request.workspace_id,
                    deployment_id=request.deployment_id,
                    integration_id=request.integration_id,
                    runtime_agent_id=request.agent_id,
                    agent_config_id=request.agent_id,
                ),
                raw_user_request=user_request,
                normalized_intent=user_request,
                domain=metadata.category,
                task_category=metadata.operation,
                tool_name=request.tool_name,
                intent_contract_id=request.intent_id,
                arguments=request.arguments,
                call_id=request.call_id,
                previous_trace_id=self._previous_trace_by_session.get(request.session_id),
                available_tools=[
                    tool.name for tool in self._definition(request.agent_id).tools
                ],
                task_relevant_tools=[],
                intent_forbidden_tools=[],
                confirmation_required_tools=[],
                prior_tool_calls=list(self._prior_calls_by_session[request.session_id]),
                previous_output_summary=self._previous_output_by_session.get(request.session_id),
                execution_status="proposed",
                tool_category=metadata.category,
                risk_level=metadata.risk_level.value,
                side_effect_type=metadata.side_effect_type,
            )
        )

    def _decision_from_evaluation(
        self,
        *,
        request: ToolProposalRequest,
        trace: AgentGuardTraceV1,
        evaluation: FirewallV2Evaluation,
        latency_ms: int,
    ) -> GuardDecisionV1:
        combined = evaluation.combined_decision or {}
        final_decision = combined.get("final_decision") or evaluation.recommendation
        if final_decision not in {"allow", "require_approval", "block"}:
            final_decision = "block"
        confidence = float(combined.get("confidence") or 0.0)
        risk = {
            "allow": max(0.05, 1.0 - confidence),
            "require_approval": max(0.70, 1.0 - min(confidence, 0.30)),
            "block": 0.95,
        }[final_decision]
        policy = evaluation.policy_evaluation or {}
        return GuardDecisionV1(
            decision_id=f"dec_{uuid4().hex}",
            trace_id=trace.trace_id,
            score_id=f"score_{trace.trace_id}",
            session_id=request.session_id,
            workspace_id=request.workspace_id,
            agent_id=request.agent_id,
            deployment_id=request.deployment_id,
            step_index=trace.step_index,
            decision=final_decision,
            tier_used="llm_judge" if any(
                result.get("tier") == "tier_3" for result in evaluation.tier_results
            ) else "static_policy",
            final_risk_score=risk,
            thresholds=DecisionThresholdsV1(),
            decision_rules_fired=[
                item.get("rule_id", "unknown")
                for item in policy.get("matched_rules", [])
            ],
            explanation=evaluation.explanation,
            latency_ms=latency_ms,
        )

    async def _create_approval(
        self,
        request: ToolProposalRequest,
        trace: AgentGuardTraceV1,
        decision: GuardDecisionV1,
        evaluation: FirewallV2Evaluation,
    ) -> str:
        approval_id = f"apr_{uuid4().hex}"
        payload = {
            "effective_decision": decision.model_dump(mode="json", by_alias=True),
            "firewall_mode": "v2",
            "evaluation": evaluation.model_dump(mode="json", by_alias=True),
        }
        approval = PendingApproval(
            approval_id=approval_id,
            decision_id=decision.decision_id,
            trace_id=trace.trace_id,
            call_id=request.call_id,
            workspace_id=request.workspace_id,
            agent_id=request.agent_id,
            deployment_id=request.deployment_id,
            integration_id=request.integration_id,
            session_id=request.session_id,
            turn_id=request.turn_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
            user_request=trace.intent.raw_user_request,
            explanation=decision.explanation,
            guard_evaluation=guard_evaluation_from_payload(payload),
            created_at=datetime.now(timezone.utc),
        )
        self._pending_by_id[approval_id] = approval
        append_jsonl(self._approvals_path, approval)
        await self._publish("approval.pending", approval.model_dump(mode="json"))
        return approval_id

    async def _record_event(
        self,
        event_type: str,
        trace: AgentGuardTraceV1,
        payload: dict,
    ) -> None:
        event = LiveEventV1(
            event_id=str(uuid4()),
            event_type=event_type,
            trace_id=trace.trace_id,
            session_id=trace.session_id,
            step_index=trace.step_index,
            agent_framework=trace.source.agent_framework,
            agent_id=trace.source.agent_id,
            workspace_id=trace.source.workspace_id,
            deployment_id=trace.source.deployment_id,
            integration_id=trace.source.integration_id,
            payload=payload,
        )
        self.trace_store.append_live_event_v1(event, namespace=self.namespace)
        await self._publish("live_event", event.model_dump(mode="json", by_alias=True))

    async def _publish(self, event: str, data: dict) -> None:
        await self.broker.publish(EventEnvelope(event=event, data=data))


def _feature_from_evaluation(
    trace: AgentGuardTraceV1,
    evaluation: FirewallV2Evaluation,
) -> TraceFeatureV1:
    normalized = evaluation.normalized_action or {}
    return TraceFeatureV1(
        feature_id=f"feat_{trace.trace_id}",
        trace_id=trace.trace_id,
        session_id=trace.session_id,
        workspace_id=trace.source.workspace_id,
        agent_id=trace.source.agent_id,
        deployment_id=trace.source.deployment_id,
        step_index=trace.step_index,
        retrieval=RetrievalFeatureV1(query_text=trace.retrieval_text.summary),
        policy_features={
            "requires_confirmation": evaluation.recommendation == "require_approval",
            "side_effect_present": bool(normalized.get("side_effect")),
            "irreversible_side_effect": normalized.get("reversible") is False,
        },
    )


def _score_from_decision(
    trace: AgentGuardTraceV1,
    decision: GuardDecisionV1,
) -> GuardScoreV1:
    risk = decision.final_risk_score
    return GuardScoreV1(
        score_id=decision.score_id or f"score_{trace.trace_id}",
        trace_id=trace.trace_id,
        feature_id=f"feat_{trace.trace_id}",
        session_id=trace.session_id,
        workspace_id=trace.source.workspace_id,
        agent_id=trace.source.agent_id,
        deployment_id=trace.source.deployment_id,
        step_index=trace.step_index,
        guard_version="agentguard_firewall_v2",
        component_scores=ComponentScoresV1(
            intent_drift=risk,
            sequence_deviation=0.0,
            argument_drift=risk,
            permission_risk=risk,
            tool_output_susceptibility=0.0,
            retrieval_risk=0.0,
            step_risk=risk,
        ),
        cumulative_after=CumulativeScoresV1(cumulative_session_risk=risk),
        dominant_signals=[decision.decision],
    )


def _executed_status(status: str) -> str:
    if status == "executed":
        return "executed"
    if status == "failed":
        return "failed"
    if status in {"blocked", "blocked_by_guard"}:
        return "blocked"
    return "skipped"
