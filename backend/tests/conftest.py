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


@atexit.register
def _remove_test_runtime_dir() -> None:
    shutil.rmtree(_TEST_RUNTIME_DIR, ignore_errors=True)