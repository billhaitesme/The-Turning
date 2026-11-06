"""Which model sits in the Mind Ladder's LOCAL deep rung — the operator's switch (2026-11-06).

Benchmarked the same day on three hard questions (clock overlaps, the Tuesday-boy puzzle, a
passage-time calculation), same deep_think prompt, think=True:
  - qwen3-abliterated:8b  — 3/3 correct, 91-190 s, all GPU, CPU ~12%; already loaded as the
    chat seat, so nothing loads or unloads.
  - qwen3-abliterated:30b-a3b — 3/3 correct, ~60 s once loaded but a 121 s first load, CPU ~51%
    (68% of it runs on CPU), and it pushes the chat seat out of VRAM.
The model cannot judge difficulty well enough to pick among more tiers, so OMEGA keeps one
choice (local vs frontier) and the OPERATOR chooses which model is "local": the light 8B day
to day, the heavier 30B for a planning session. A recorded console action, like the breaker;
no registry command maps here, so the model cannot flip it.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from services.tool_contracts import utc_now_iso

CHOICES: List[Dict[str, str]] = [
    {"model": "huihui_ai/qwen3-abliterated:8b", "label": "8B",
     "note": "light: GPU only, already loaded, ~1.5-3 min"},
    {"model": "huihui_ai/qwen3-abliterated:30b-a3b", "label": "30B",
     "note": "heavy: ~2 min load, ~50% CPU, evicts the chat seat"},
]
DEFAULT_MODEL = CHOICES[0]["model"]


def _path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "deep_seat.json"


def state() -> Dict[str, Any]:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("history", [])
    allowed = {c["model"] for c in CHOICES}
    if data.get("model") not in allowed:
        # never set (or a stale value): .env's DEEP_LOCAL_MODEL if it names a choice, else the 8B
        env = os.getenv("DEEP_LOCAL_MODEL", "").strip()
        data["model"] = env if env in allowed else DEFAULT_MODEL
    data["choices"] = deepcopy(CHOICES)
    return data


def local_model() -> str:
    return state()["model"]


def set_local_model(model: str, *, changed_by: str, channel: str) -> Dict[str, Any]:
    allowed = {c["model"] for c in CHOICES}
    if model not in allowed:
        raise ValueError(f"'{model}' is not a deep-rung choice; choose one of {sorted(allowed)}.")
    data = state()
    now = utc_now_iso()
    data.update({"model": model, "changed_at": now, "changed_by": changed_by})
    data["history"] = (data.get("history") or [])[-199:] + [
        {"model": model, "at": now, "by": changed_by, "channel": channel}]
    stored = {k: v for k, v in data.items() if k != "choices"}
    _path().parent.mkdir(parents=True, exist_ok=True)
    _path().write_text(json.dumps(stored, indent=2, ensure_ascii=False), encoding="utf-8")
    return state()
