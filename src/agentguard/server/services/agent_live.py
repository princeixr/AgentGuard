"""Live state and SSE fan-out backed by canonical agent runtime events."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress

from agentguard.server.models import CurrentInterception, EventEnvelope
from agentguard.server.repositories.base import DashboardRepository
from agentguard.server.services.live import EventBroker
from agentguard.server.services.query import DashboardQueryService
from agentguard.tracing.schema_v1 import LiveEventV1

INTERVENTION_DECISIONS = {"review", "require_approval", "block"}
TERMINAL_EVENTS = {"tool_executed", "tool_blocked", "tool_failed"}
logger = logging.getLogger(__name__)


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
        self._initialized = False

    def current(self, agent_id: str) -> CurrentInterception:
        self._initialize_from_history()
        self._consume_new_events()
        state = self._states.get(agent_id)
        if state is not None:
            return state
        return self._idle_state(agent_id)

    async def subscribe(self, agent_id: str):
        subscription = self.broker.subscribe()
        pending_event = asyncio.create_task(anext(subscription))
        # Async-generator setup is deferred until its first iteration. Let the
        # broker register this subscriber before the monitor can publish.
        await asyncio.sleep(0)
        self._ensure_monitor()
        try:
            yield EventEnvelope(
                event="state",
                data=self.current(agent_id).model_dump(mode="json"),
            )
            while True:
                envelope = await pending_event
                pending_event = asyncio.create_task(anext(subscription))
                if envelope.data.get("agent_id") == agent_id:
                    yield envelope
        finally:
            pending_event.cancel()
            with suppress(asyncio.CancelledError):
                await pending_event
            await subscription.aclose()

    def _ensure_monitor(self) -> None:
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor())

    async def _monitor(self) -> None:
        self._initialize_from_history()
        while True:
            try:
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
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Live-event polling failed; retrying on the next interval."
                )
            await asyncio.sleep(self.poll_interval_seconds)

    def _consume_new_events(self) -> list[LiveEventV1]:
        self._initialize_from_history()
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

    def _initialize_from_history(self) -> None:
        if self._initialized:
            return
        events = sorted(self.repository.live_events(), key=lambda item: item.timestamp)
        self._seen_event_ids.update(event.event_id for event in events)
        latest_by_agent: dict[str, LiveEventV1] = {}
        for event in events:
            latest_by_agent[event.agent_id] = event
        for event in latest_by_agent.values():
            self._apply_event(event)
        self._initialized = True

    def _apply_event(self, event: LiveEventV1) -> None:
        detail = None
        total_steps = event.step_index or 0
        if event.event_type in {
            "guard_decided",
            "firewall_v2_evaluated",
            *TERMINAL_EVENTS,
        } and event.trace_id:
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
        existing = self._states.get(event.agent_id)
        status = (
            existing.status
            if existing is not None
            and existing.current_trace_id == event.trace_id
            else "running"
        )
        if (
            event.event_type in {"guard_decided", "firewall_v2_evaluated"}
            and detail is not None
            and detail.item.decision in INTERVENTION_DECISIONS
        ):
            status = "paused"
        elif event.event_type in TERMINAL_EVENTS:
            status = "completed"
        self._states[event.agent_id] = CurrentInterception(
            status=status,
            event_source="google_adk_runtime",
            firewall_mode=os.environ.get("AGENTGUARD_FIREWALL_MODE", "v2"),
            guard_version=_guard_version(),
            agent_id=event.agent_id,
            session_id=event.session_id,
            current_trace_id=event.trace_id,
            current_step=event.step_index or 0,
            total_steps=max(total_steps, event.step_index or 0),
            detail=detail,
        )

    def _idle_state(self, agent_id: str) -> CurrentInterception:
        return CurrentInterception(
            status="idle",
            event_source="google_adk_runtime",
            firewall_mode=os.environ.get("AGENTGUARD_FIREWALL_MODE", "v2"),
            guard_version=_guard_version(),
            agent_id=agent_id,
        )


def _guard_version() -> str:
    return "agentguard_firewall_v2"
