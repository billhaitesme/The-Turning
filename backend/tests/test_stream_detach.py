"""Detached chat streams (2026-11-06): a reply is finished and saved even if the client leaves."""
import threading
import time

import pytest

from services.stream_detach import KEEPALIVE, detach_stream


def test_events_pass_through_in_order():
    assert list(detach_stream(iter(["a", "b", "c"]))) == ["a", "b", "c"]


def test_quiet_runtime_sends_keepalive_comments():
    def slow():
        time.sleep(0.35)
        yield "data: reply\n\n"

    out = list(detach_stream(slow(), heartbeat_seconds=0.1))
    assert out[-1] == "data: reply\n\n"
    assert KEEPALIVE in out
    assert KEEPALIVE.startswith(":")  # an SSE comment: clients ignore it


def test_source_runs_to_the_end_after_the_client_hangs_up():
    saved = threading.Event()

    def chat():
        yield "data: phase\n\n"
        time.sleep(0.2)          # the model still generating
        yield "data: delta\n\n"
        saved.set()              # stands in for add_message(...) after the stream

    stream = detach_stream(chat(), heartbeat_seconds=0.05)
    assert next(stream) == "data: phase\n\n"
    stream.close()               # the phone gave up
    assert saved.wait(2.0), "the reply was not saved after the client disconnected"


def test_source_starts_even_if_the_client_never_reads():
    saved = threading.Event()

    def chat():
        saved.set()
        yield "data: never read\n\n"

    detach_stream(chat())        # the phone hung up before the body was ever pulled
    assert saved.wait(2.0), "generation never started because nobody read the stream"


def test_source_errors_still_reach_the_reader():
    def broken():
        yield "data: x\n\n"
        raise RuntimeError("boom")

    stream = detach_stream(broken())
    assert next(stream) == "data: x\n\n"
    with pytest.raises(RuntimeError, match="boom"):
        next(stream)
