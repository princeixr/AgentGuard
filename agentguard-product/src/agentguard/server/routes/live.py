"""Live interception and SSE routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from agentguard.server.dependencies import require_operator_access, get_demo_runtime
from agentguard.server.models import CurrentInterception
from agentguard.server.services.live import DemoRuntimeService

router = APIRouter(tags=["live"], dependencies=[Depends(require_operator_access)])


@router.get("/interceptions/current", response_model=CurrentInterception)
def current_interception(
    runtime: DemoRuntimeService = Depends(get_demo_runtime),
) -> CurrentInterception:
    return runtime.current()


@router.get("/events/stream")
async def event_stream(runtime: DemoRuntimeService = Depends(get_demo_runtime)):
    async def generate():
        initial = runtime.current().model_dump(mode="json")
        yield _format_sse("state", initial)
        async for envelope in runtime.broker.subscribe():
            yield _format_sse(envelope.event, envelope.data)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
