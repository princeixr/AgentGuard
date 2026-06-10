"""AgentGuard client protocol and production HTTP transport."""

from __future__ import annotations

import json
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agentguard_sdk.models import (
    AgentRegistration,
    EnforcementDecision,
    OutcomeReport,
    PendingApproval,
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


class HttpAgentGuardClient:
    """Synchronous HTTP client for runtime tool-call enforcement."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
        fail_closed: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.fail_closed = fail_closed

    def register(self, registration: AgentRegistration) -> None:
        try:
            self._request("POST", "/api/v1/agents/register", registration.model_dump(mode="json"))
        except Exception:
            if not self.fail_closed:
                raise

    def start_turn(self, request: TurnStart) -> TurnStartResult:
        try:
            payload = self._request("POST", "/api/v1/turns/start", request.model_dump(mode="json"))
            return TurnStartResult.model_validate(payload)
        except Exception:
            if not self.fail_closed:
                raise
            return TurnStartResult(
                intent_id=f"intent_unavailable_{request.turn_id}",
                turn_id=request.turn_id,
                accepted=False,
            )

    def evaluate(self, proposal: ToolProposal) -> EnforcementDecision:
        try:
            payload = self._request(
                "POST",
                "/api/v1/tool-proposals/evaluate",
                proposal.model_dump(mode="json"),
            )
            return EnforcementDecision.model_validate(payload)
        except Exception as exc:
            if not self.fail_closed:
                raise
            return EnforcementDecision(
                call_id=proposal.call_id,
                decision="require_approval",
                explanation=f"AgentGuard API unavailable; failed closed: {exc}",
            )

    def report_outcome(self, outcome: OutcomeReport) -> None:
        try:
            self._request("POST", "/api/v1/tool-outcomes", outcome.model_dump(mode="json"))
        except Exception:
            if not self.fail_closed:
                raise

    def get_approval(self, approval_id: str) -> PendingApproval:
        payload = self._request("GET", f"/api/v1/approvals/{approval_id}")
        return PendingApproval.model_validate(payload)

    def wait_for_approval(
        self,
        approval_id: str,
        *,
        timeout_seconds: float = 60.0,
        poll_interval_seconds: float = 1.0,
    ) -> PendingApproval:
        deadline = time.monotonic() + timeout_seconds
        while True:
            approval = self.get_approval(approval_id)
            if approval.status != "pending":
                return approval
            if time.monotonic() >= deadline:
                return approval.model_copy(update={"status": "expired"})
            time.sleep(poll_interval_seconds)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AgentGuard API returned {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"AgentGuard API request failed: {exc}") from exc
        return json.loads(raw) if raw else {}
