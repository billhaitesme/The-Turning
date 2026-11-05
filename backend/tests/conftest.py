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


@atexit.register
def _remove_test_runtime_dir() -> None:
    shutil.rmtree(_TEST_RUNTIME_DIR, ignore_errors=True)