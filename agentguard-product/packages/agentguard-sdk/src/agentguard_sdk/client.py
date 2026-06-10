"""Client protocol and local fake used before transport implementation."""

from __future__ import annotations

from typing import Protocol

from agentguard_sdk.models import (
    AgentRegistration,
    EnforcementDecision,
    OutcomeReport,
    ToolProposal,
    TurnStart,
    TurnStartResult,
)


class AgentGuardClient(Protocol):
    def register(self, registration: AgentRegistration) -> None: ...

    def start_turn(self, request: TurnStart) -> TurnStartResult: ...

    def evaluate(self, proposal: ToolProposal) -> EnforcementDecision: ...

    def report_outcome(self, outcome: OutcomeReport) -> None: ...


class FakeAgentGuardClient:
    """Deterministic test client; it is not an enforcement implementation."""

    def __init__(self, decision: str = "allow"):
        if decision not in {"allow", "require_approval", "block"}:
            raise ValueError(f"Unsupported fake decision: {decision}")
        self.decision = decision
        self.registrations: list[AgentRegistration] = []
        self.turns: list[TurnStart] = []
        self.proposals: list[ToolProposal] = []
        self.outcomes: list[OutcomeReport] = []

    def register(self, registration: AgentRegistration) -> None:
        self.registrations.append(registration)

    def start_turn(self, request: TurnStart) -> TurnStartResult:
        self.turns.append(request)
        return TurnStartResult(
            intent_id=f"intent_{request.turn_id}",
            turn_id=request.turn_id,
        )

    def evaluate(self, proposal: ToolProposal) -> EnforcementDecision:
        self.proposals.append(proposal)
        return EnforcementDecision(
            call_id=proposal.call_id,
            decision=self.decision,
            explanation=f"Fake client returned {self.decision}.",
        )

    def report_outcome(self, outcome: OutcomeReport) -> None:
        self.outcomes.append(outcome)
