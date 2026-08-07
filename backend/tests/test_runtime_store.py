from services.runtime_store import (
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeEventType,
    RuntimeStore,
)


def test_runtime_store_reports_persisted_queue_and_session():
    store = RuntimeStore()
    store.touch_client("ios-device")
    store.set_session("session-1")
    snapshot = store.snapshot(
        tool_requests=[
            {"status": "awaiting_approval"},
            {"status": "completed"},
            {"status": "running"},
        ],
        chronicle_events=4,
    )
    assert snapshot["tool_queue"] == 2
    assert snapshot["connected_clients"] == 1
    assert snapshot["current_session"] == "session-1"
    assert snapshot["chronicle_events"] == 4
    assert snapshot["streaming_state"] == "idle"


def test_stream_lifecycle_is_observed_without_simulation():
    store = RuntimeStore()
    store.begin_stream("session-2")
    active = store.snapshot(tool_requests=[], chronicle_events=0)
    assert active["streaming_state"] == "streaming"
    assert active["active_streams"] == 1

    store.end_stream(42.5)
    idle = store.snapshot(tool_requests=[], chronicle_events=0)
    assert idle["streaming_state"] == "idle"
    assert idle["latency_ms"] == 42.5


def test_event_bus_fans_out_typed_sse_events():
    bus = RuntimeEventBus()
    subscriber_id, queue = bus.subscribe()
    event = RuntimeEvent.create(RuntimeEventType.STATUS, {"online": True})
    bus.publish(event)
    received = queue.get_nowait()
    assert received.event_type is RuntimeEventType.STATUS
    assert received.payload == {"online": True}
    encoded = received.as_sse().decode("utf-8")
    assert encoded.startswith("event: status\n")
    assert '"type":"status"' in encoded
    bus.unsubscribe(subscriber_id)
