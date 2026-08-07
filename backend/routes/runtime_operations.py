"""Epoch IX-B measured operations telemetry and typed SSE feed."""

from __future__ import annotations

import asyncio
from queue import Empty
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from routes.mobile import (
    build_mobile_diagnostics,
    build_runtime_status,
    latest_conversation_id,
    load_mobile_chronicle,
    require_mobile_auth,
)
from services.runtime_store import (
    RuntimeEvent,
    RuntimeEventType,
    runtime_event_bus,
    runtime_store,
)
from services.tool_request_store import list_tool_requests


EVENT_HEARTBEAT_SECONDS = 5.0

router = APIRouter(
    prefix="/api/mobile/v1",
    tags=["bridge-zero-operations"],
    dependencies=[Depends(require_mobile_auth)],
)


def _observe_client(client_id: Optional[str]) -> None:
    runtime_store.touch_client(client_id)


def _telemetry_payload(client_id: Optional[str]) -> dict[str, Any]:
    _observe_client(client_id)
    current_session = latest_conversation_id()
    runtime_store.set_session(current_session)
    return runtime_store.snapshot(
        tool_requests=list_tool_requests(),
        chronicle_events=len(load_mobile_chronicle()),
    )


@router.get("/telemetry")
def telemetry(
    client_id: Optional[str] = Header(default=None, alias="X-Bridge-Client-ID"),
) -> dict[str, Any]:
    payload = _telemetry_payload(client_id)
    runtime_event_bus.publish(RuntimeEvent.create(RuntimeEventType.TELEMETRY, payload))
    return payload


@router.get("/events")
async def typed_runtime_events(
    client_id: Optional[str] = Header(default=None, alias="X-Bridge-Client-ID"),
) -> StreamingResponse:
    _observe_client(client_id)
    subscriber_id, queue = runtime_event_bus.subscribe()

    async def events():
        try:
            initial_events = (
                RuntimeEvent.create(RuntimeEventType.STATUS, build_runtime_status()),
                RuntimeEvent.create(RuntimeEventType.DIAGNOSTICS, build_mobile_diagnostics()),
                RuntimeEvent.create(
                    RuntimeEventType.SESSION,
                    {"current_session": latest_conversation_id()},
                ),
                RuntimeEvent.create(
                    RuntimeEventType.CHRONICLE,
                    {"entries": load_mobile_chronicle()},
                ),
                RuntimeEvent.create(RuntimeEventType.TELEMETRY, _telemetry_payload(client_id)),
            )
            for event in initial_events:
                yield event.as_sse()
            while True:
                try:
                    event = await asyncio.to_thread(
                        queue.get,
                        True,
                        EVENT_HEARTBEAT_SECONDS,
                    )
                except Empty:
                    _observe_client(client_id)
                    event = RuntimeEvent.create(
                        RuntimeEventType.TELEMETRY,
                        _telemetry_payload(client_id),
                    )
                yield event.as_sse()
        finally:
            runtime_event_bus.unsubscribe(subscriber_id)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
