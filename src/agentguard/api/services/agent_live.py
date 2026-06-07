"""Live state and SSE fan-out backed by canonical agent runtime events."""

from __future__ import annotations

import asyncio

from agentguard.api.models import CurrentInterception, EventEnvelope
from agentguard.api.repositories.base import DashboardRepository
from agentguard.api.services.live import EventBroker
from agentguard.api.services.query import DashboardQueryService
from agentguard.tracing.schema_v1 import LiveEventV1

INTERVENTION_DECISIONS = {"review", "require_approval", "block"}
TERMINAL_EVENTS = {"tool_executed", "tool_blocked", "tool_failed"}


class AgentLiveRuntimeService:
    def __init__(
        self,
        repository: DashboardRepository,
        query_service: DashboardQueryService,
        poll_interval_seconds: float = 0.2,
    ):
        self.repository = repository
        self.query_service = query_service
        self.poll_interval_seconds = poll_interval_seconds
        self.broker = EventBroker()
        self._states: dict[str, CurrentInterception] = {}
        self._seen_event_ids: set[str] = set()
        self._monitor_task: asyncio.Task | None = None

    def current(self, agent_id: str) -> CurrentInterception:
        self._consume_new_events()
        state = self._states.get(agent_id)
        if state is not None:
            return state
        return self._state_from_history(agent_id)

    async def subscribe(self, agent_id: str):
        self._ensure_monitor()
        async for envelope in self.broker.subscribe():
            if envelope.data.get("agent_id") == agent_id:
                yield envelope

    def _ensure_monitor(self) -> None:
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor())

    async def _monitor(self) -> None:
        while True:
            for event in self._new_events():
                self._seen_event_ids.add(event.event_id)
                self._apply_event(event)
                await self.broker.publish(
                    EventEnvelope(
                        event="live_event",
                        data=event.model_dump(mode="json", by_alias=True),
                    )
                )
                await self.broker.publish(
                    EventEnvelope(
                        event="state",
                        data=self.current(event.agent_id).model_dump(mode="json"),
                    )
                )
            await asyncio.sleep(self.poll_interval_seconds)

    def _consume_new_events(self) -> list[LiveEventV1]:
        new_events = self._new_events()
        for event in new_events:
            self._seen_event_ids.add(event.event_id)
            self._apply_event(event)
        return new_events

    def _new_events(self) -> list[LiveEventV1]:
        events = sorted(self.repository.live_events(), key=lambda item: item.timestamp)
        return [
            event for event in events if event.event_id not in self._seen_event_ids
        ]

    def _apply_event(self, event: LiveEventV1) -> None:
        detail = None
        total_steps = event.step_index or 0
        if event.event_type in {"guard_decided", *TERMINAL_EVENTS} and event.trace_id:
            try:
                detail = self.query_service.memory_detail(
                    event.trace_id,
                    agent_id=event.agent_id,
                )
                session = self.query_service.session(
                    event.session_id,
                    agent_id=event.agent_id,
                )
                total_steps = len(session.steps) if session else total_steps
            except (KeyError, StopIteration):
                detail = None
        status = "running"
        if (
            event.event_type == "guard_decided"
            and detail is not None
            and detail.item.decision in INTERVENTION_DECISIONS
        ):
            status = "paused"
        elif event.event_type in TERMINAL_EVENTS:
            status = "completed"
        self._states[event.agent_id] = CurrentInterception(
            status=status,
            agent_id=event.agent_id,
            session_id=event.session_id,
            current_trace_id=event.trace_id,
            current_step=event.step_index or 0,
            total_steps=max(total_steps, event.step_index or 0),
            detail=detail,
        )

    def _state_from_history(self, agent_id: str) -> CurrentInterception:
        events = [
            event
            for event in self.repository.live_events()
            if event.agent_id == agent_id
        ]
        if not events:
            return CurrentInterception(status="idle", agent_id=agent_id)
        latest_session = max(events, key=lambda item: item.timestamp).session_id
        for event in sorted(
            (item for item in events if item.session_id == latest_session),
            key=lambda item: item.timestamp,
        ):
            self._apply_event(event)
        return self._states[agent_id]
