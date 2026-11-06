"""Detached chat streams — a reply is finished and saved even if the client hangs up (2026-11-06).

Why: the chat generators save the assistant reply only AFTER the last event is sent. Starlette
stops pulling a generator the moment the client disconnects, so the save code never ran. Phones
disconnect easily here: the model swap before the first token takes ~20 s on this 8 GB GPU,
Android's OkHttp gives up after 10 s of silence and iOS URLSession after 60 s. Result seen
2026-11-06: Ollama generated the reply (200, 50 s / 3m40s) and the operator got silence.

How: the real generator runs to completion on its own thread and feeds a queue; the HTTP side
reads that queue and, while the runtime is quiet, sends an SSE comment (": keep-alive") every few
seconds. SSE clients ignore comment lines (both Bridge Zero parsers only read "data:" lines), and
the trickle keeps idle-read timeouts from firing in the first place.
"""
from __future__ import annotations

import queue
import sys
import threading
from typing import Iterator

KEEPALIVE = ": keep-alive\n\n"
_DONE = object()


class _Failure:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc


def detach_stream(source: Iterator[str], heartbeat_seconds: float = 5.0) -> Iterator[str]:
    """Yield `source`'s events; `source` itself always runs to the end, client or no client."""
    channel: "queue.Queue[object]" = queue.Queue()

    def pump() -> None:
        try:
            for item in source:
                channel.put(item)
        except BaseException as exc:  # noqa: BLE001 — handed to the reader, never swallowed
            # The reader may be long gone (client hung up), so say it out loud too.
            print(f"chat-stream-pump: stream failed: {exc!r}", file=sys.stderr, flush=True)
            channel.put(_Failure(exc))
        finally:
            channel.put(_DONE)

    # Start NOW, not on the first read: a client that hangs up before the server even begins
    # sending (live test 2026-11-06: 3 s phone timeout during the memory search) would otherwise
    # leave the generator never started and the reply never made.
    threading.Thread(target=pump, name="chat-stream-pump", daemon=True).start()
    return _read(channel, heartbeat_seconds)


def _read(channel: "queue.Queue[object]", heartbeat_seconds: float) -> Iterator[str]:
    while True:
        try:
            item = channel.get(timeout=heartbeat_seconds)
        except queue.Empty:
            yield KEEPALIVE
            continue
        if item is _DONE:
            return
        if isinstance(item, _Failure):
            raise item.exc
        yield item  # if the client is gone, this generator is simply dropped; pump() carries on
