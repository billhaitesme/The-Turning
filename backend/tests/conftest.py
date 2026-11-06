"""Test isolation for mutable runtime stores."""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import tempfile


_TEST_RUNTIME_DIR = Path(tempfile.mkdtemp(prefix="omega-arc-tests-"))
os.environ["OMEGA_TOOL_DATA_DIR"] = str(_TEST_RUNTIME_DIR / "tool-data")
# The conversation store too: without this, test conversations land in the live omega_arc.db
# and surface in the consoles' Recents rail (observed 2026-11-05).
os.environ["TURNING_DB_PATH"] = str(_TEST_RUNTIME_DIR / "omega_arc_test.db")

# app.py loads the repository's live .env with override=True at import, which can carry the
# operator's ENABLE_AGENT_LOOP=true — and the suite must NEVER reach the real model house.
# Import app now (so dotenv has run), then pin the loop off; agent_loop reads the env at call
# time, so tests that want the loop opt in explicitly (monkeypatch) with scripted seats.
import app  # noqa: E402,F401  (import order is the point)

os.environ["ENABLE_AGENT_LOOP"] = "false"


import socket  # noqa: E402

import pytest  # noqa: E402

# Public-looking hosts the tests use, pinned to a public address. Without this the web_fetch
# private-address guard answers to whatever DNS the PC is on: hotel Wi-Fi (2026-11-06) resolved
# example.com to 127.0.0.1, so the guard refused it and two tests failed for network reasons.
_PINNED_PUBLIC_HOSTS = {"example.com": "93.184.215.14"}


@pytest.fixture(autouse=True)
def _hermetic_dns(monkeypatch):
    real_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host, *args, **kwargs):
        pinned = _PINNED_PUBLIC_HOSTS.get(str(host).lower())
        if pinned:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (pinned, 0))]
        return real_getaddrinfo(host, *args, **kwargs)

    from services.adapters import web_fetch
    monkeypatch.setattr(web_fetch.socket, "getaddrinfo", fake_getaddrinfo)


@atexit.register
def _remove_test_runtime_dir() -> None:
    shutil.rmtree(_TEST_RUNTIME_DIR, ignore_errors=True)