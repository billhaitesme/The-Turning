"""Authoritative Epoch IX-B runtime telemetry and typed event bus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from queue import Empty, Full, Queue
from threading import RLock
import time
from typing import Any, Dict, Optional
import uuid

try:
    import psutil
except ImportError:  # Telemetry stays explicitly unavailable until installed.
    psutil = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RuntimeEventType(str, Enum):
    TELEMETRY = "telemetry"
    STATUS = "status"
    DIAGNOSTICS = "diagnostics"
    STREAMING = "streaming"
    SESSION = "session"
    CHRONICLE = "chronicle"


@dataclass(frozen=True)
class RuntimeEvent:
    event_id: str
    event_type: RuntimeEventType
    occurred_at: str
    payload: Dict[str, Any]

    @classmethod
    def create(cls, event_type: RuntimeEventType, payload: Dict[str, Any]) -> "RuntimeEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            occurred_at=utc_now(),
            payload=dict(payload),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.event_type.value,
            "occurred_at": self.occurred_at,
            "payload": self.payload,
        }

    def as_sse(self) -> bytes:
        data = json.dumps(self.as_dict(), separators=(",", ":"), ensure_ascii=False)
        return f"event: {self.event_type.value}\ndata: {data}\n\n".encode("utf-8")


class RuntimeEventBus:
    """Thread-safe fan-out bus; subscribers receive only real published events."""

    def __init__(self, subscriber_capacity: int = 100) -> None:
        self._lock = RLock()
        self._capacity = subscriber_capacity
        self._subscribers: Dict[str, Queue[RuntimeEvent]] = {}

    def subscribe(self) -> tuple[str, Queue[RuntimeEvent]]:
        subscriber_id = str(uuid.uuid4())
        queue: Queue[RuntimeEvent] = Queue(maxsize=self._capacity)
        with self._lock:
            self._subscribers[subscriber_id] = queue
        return subscriber_id, queue

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def publish(self, event: RuntimeEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers.values())
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except Full:
                try:
                    queue.get_nowait()
                except Empty:
                    pass
                try:
                    queue.put_nowait(event)
                except Full:
                    pass


class RuntimeStore:
    """Single in-process authority for observed IX-B operational state."""

    CLIENT_TTL_SECONDS = 30.0

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = time.monotonic()
        self._clients: Dict[str, float] = {}
        self._active_streams = 0
        self._current_session: Optional[str] = None
        self._last_stream_latency_ms: Optional[float] = None
        if psutil is not None:
            psutil.cpu_percent(interval=None)

    def touch_client(self, client_id: Optional[str]) -> None:
        candidate = str(client_id or "").strip()
        if not candidate:
            return
        now = time.monotonic()
        with self._lock:
            self._clients[candidate] = now
            self._expire_clients(now)

    def set_session(self, session_id: Optional[str]) -> None:
        with self._lock:
            self._current_session = str(session_id) if session_id else None

    def begin_stream(self, session_id: str) -> int:
        with self._lock:
            self._active_streams += 1
            self._current_session = session_id
            return self._active_streams

    def end_stream(self, latency_ms: float) -> int:
        with self._lock:
            self._active_streams = max(0, self._active_streams - 1)
            self._last_stream_latency_ms = max(0.0, float(latency_ms))
            return self._active_streams

    def snapshot(
        self,
        *,
        tool_requests: list[Dict[str, Any]],
        chronicle_events: int,
    ) -> Dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._expire_clients(now)
            connected_clients = len(self._clients)
            active_streams = self._active_streams
            current_session = self._current_session
            last_latency = self._last_stream_latency_ms

        pending_states = {"pending", "awaiting_approval", "approved", "running"}
        tool_queue = sum(
            1
            for request in tool_requests
            if isinstance(request, dict) and str(request.get("status") or "").lower() in pending_states
        )
        cpu_percent: Optional[float] = None
        ram_used_bytes: Optional[int] = None
        ram_total_bytes: Optional[int] = None
        if psutil is not None:
            cpu_percent = round(float(psutil.cpu_percent(interval=None)), 1)
            memory = psutil.virtual_memory()
            ram_used_bytes = int(memory.used)
            ram_total_bytes = int(memory.total)

        return {
            "observed_at": utc_now(),
            "uptime_seconds": max(0, int(now - self._started_at)),
            "cpu_percent": cpu_percent,
            "ram_used_bytes": ram_used_bytes,
            "ram_total_bytes": ram_total_bytes,
            "latency_ms": last_latency,
            "tool_queue": tool_queue,
            "streaming_state": "streaming" if active_streams > 0 else "idle",
            "active_streams": active_streams,
            "connected_clients": connected_clients,
            "current_session": current_session,
            "chronicle_events": max(0, int(chronicle_events)),
        }

    def _expire_clients(self, now: float) -> None:
        expired = [
            client_id
            for client_id, last_seen in self._clients.items()
            if now - last_seen > self.CLIENT_TTL_SECONDS
        ]
        for client_id in expired:
            self._clients.pop(client_id, None)


runtime_event_bus = RuntimeEventBus()
runtime_store = RuntimeStore()


def observe_streaming_response(response: Any, session_id: str) -> Any:
    """Observe the shared conversation stream once for every client surface."""
    body_iterator = getattr(response, "body_iterator", None)
    if body_iterator is None:
        return response

    started_at = time.perf_counter()
    active_streams = runtime_store.begin_stream(session_id)
    runtime_event_bus.publish(RuntimeEvent.create(
        RuntimeEventType.SESSION,
        {"current_session": session_id},
    ))
    runtime_event_bus.publish(RuntimeEvent.create(
        RuntimeEventType.STREAMING,
        {
            "state": "streaming",
            "session_id": session_id,
            "active_streams": active_streams,
        },
    ))

    async def observed_body():
        try:
            async for chunk in body_iterator:
                yield chunk
        finally:
            latency_ms = (time.perf_counter() - started_at) * 1_000
            remaining_streams = runtime_store.end_stream(latency_ms)
            runtime_event_bus.publish(RuntimeEvent.create(
                RuntimeEventType.STREAMING,
                {
                    "state": "streaming" if remaining_streams else "idle",
                    "session_id": session_id,
                    "active_streams": remaining_streams,
                    "latency_ms": round(latency_ms, 3),
                },
            ))

    response.body_iterator = observed_body()
    return response
