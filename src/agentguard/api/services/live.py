"""In-process deterministic live-demo playback and event distribution."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from agentguard.api.models import (
    ApprovalRecord,
    ApprovalRequest,
    CurrentInterception,
    DemoStartResponse,
    EventEnvelope,
)
from agentguard.api.repositories.base import DashboardRepository
from agentguard.api.services.query import DashboardQueryService


class EventBroker:
    def __init__(self):
        self._subscribers: set[asyncio.Queue[EventEnvelope]] = set()

    async def publish(self, event: EventEnvelope) -> None:
        for queue in list(self._subscribers):
            await queue.put(event)

    async def subscribe(self) -> AsyncIterator[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)


class DemoRuntimeService:
    def __init__(
        self,
        repository: DashboardRepository,
        query_service: DashboardQueryService,
        step_delay_seconds: float = 0.35,
    ):
        self.repository = repository
        self.query_service = query_service
        self.step_delay_seconds = step_delay_seconds
        self.broker = EventBroker()
        self._state = CurrentInterception(status="idle")
        self._task: asyncio.Task | None = None

    def current(self, agent_id: str | None = None) -> CurrentInterception:
        if agent_id is not None and self._state.agent_id not in {None, agent_id}:
            return CurrentInterception(status="idle", agent_id=agent_id)
        return self._state

    async def start(self, scenario_id: str, agent_id: str | None = None) -> DemoStartResponse:
        scenario = next(
            (
                item
                for item in self.repository.scenarios()
                if item.scenario_id == scenario_id
            ),
            None,
        )
        if scenario is None:
            raise KeyError(scenario_id)
        if self._task and not self._task.done():
            self._task.cancel()

        session_id = f"demo_{scenario_id}"
        detail = self.query_service.session(session_id, agent_id=agent_id)
        if detail is None:
            raise KeyError(session_id)
        self._state = CurrentInterception(
            status="running",
            agent_id=agent_id,
            scenario_id=scenario_id,
            session_id=session_id,
            current_step=0,
            total_steps=len(detail.steps),
        )
        await self.broker.publish(
            EventEnvelope(
                event="scenario_started",
                data=self._state.model_dump(mode="json"),
            )
        )
        self._task = asyncio.create_task(self._play(session_id))
        return DemoStartResponse(
            scenario_id=scenario_id,
            session_id=session_id,
            status="running",
        )

    async def resolve(
        self,
        trace_id: str,
        request: ApprovalRequest,
    ) -> ApprovalRecord:
        if self._state.status != "paused" or self._state.current_trace_id != trace_id:
            raise ValueError("Trace is not awaiting an operator decision.")
        approval = ApprovalRecord(
            trace_id=trace_id,
            action=request.action,
            actor=request.actor,
            note=request.note,
            timestamp=datetime.now(timezone.utc),
        )
        self._state = self._state.model_copy(
            update={"status": "completed", "approval": approval}
        )
        await self.broker.publish(
            EventEnvelope(
                event="approval_resolved",
                data=approval.model_dump(mode="json"),
            )
        )
        await self.broker.publish(
            EventEnvelope(
                event="scenario_completed",
                data=self._state.model_dump(mode="json"),
            )
        )
        return approval

    async def reset(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._state = CurrentInterception(status="idle")
        await self.broker.publish(EventEnvelope(event="demo_reset", data={}))

    async def _play(self, session_id: str) -> None:
        session_events = [
            event
            for event in self.repository.live_events()
            if event.session_id == session_id
            and (
                self._state.agent_id is None
                or event.agent_id == self._state.agent_id
            )
        ]
        session_events.sort(key=lambda item: item.timestamp)
        try:
            for event in session_events:
                await asyncio.sleep(self.step_delay_seconds)
                detail = (
                    self.query_service.memory_detail(
                        event.trace_id,
                        agent_id=self._state.agent_id,
                    )
                    if event.trace_id
                    else None
                )
                self._state = self._state.model_copy(
                    update={
                        "current_trace_id": event.trace_id,
                        "current_step": event.step_index or self._state.current_step,
                        "detail": detail,
                    }
                )
                await self.broker.publish(
                    EventEnvelope(
                        event="live_event",
                        data=event.model_dump(mode="json", by_alias=True),
                    )
                )
                if (
                    event.event_type == "guard_decided"
                    and detail is not None
                    and detail.item.decision in {"review", "require_approval", "block"}
                ):
                    self._state = self._state.model_copy(update={"status": "paused"})
                    await self.broker.publish(
                        EventEnvelope(
                            event="interception_paused",
                            data=self._state.model_dump(mode="json"),
                        )
                    )
                    return
            self._state = self._state.model_copy(update={"status": "completed"})
            await self.broker.publish(
                EventEnvelope(
                    event="scenario_completed",
                    data=self._state.model_dump(mode="json"),
                )
            )
        except asyncio.CancelledError:
            return
