"""OMEGA's speaking voice — a real, changeable setting (2026-11-06).

Bill asked OMEGA whether its voice could be changed and for options. It could not answer: the
voice was a fixed env value (VOICE_TTS_VOICE, default bm_fable) with no picker, no command and no
self-knowledge. Now the voice is a stored setting; the installed English voices are read from the
Kokoro voices file itself (never a hand-kept list); the console has a picker; and OMEGA can list
and change its own voice with direct commands (low risk, reversible, logged).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from services.tool_contracts import utc_now_iso

VOICES_FILE = Path(__file__).resolve().parents[1] / "models" / "voice" / "voices-v1.0.bin"
DEFAULT_VOICE = "bm_fable"
# Kokoro's naming: first letter = accent, second = gender. Only English voices are offered:
# the house speaks en-gb / en-us.
_ACCENT = {"a": "American", "b": "British"}
_GENDER = {"f": "female", "m": "male"}


def _path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "voice_setting.json"


def installed_voices() -> List[Dict[str, str]]:
    try:
        import numpy as np
        with np.load(VOICES_FILE) as data:
            names = sorted(data.files)
    except Exception:  # noqa: BLE001 — no voice files means no choices, never a crash
        return []
    voices = []
    for name in names:
        accent, gender = _ACCENT.get(name[:1]), _GENDER.get(name[1:2])
        if accent and gender and name[2:3] == "_":
            voices.append({"id": name, "label": f"{name[3:].capitalize()} ({accent} {gender})"})
    return voices


def current_voice() -> str:
    try:
        stored = json.loads(_path().read_text(encoding="utf-8")).get("voice")
    except (OSError, json.JSONDecodeError, AttributeError):
        stored = None
    return stored or os.getenv("VOICE_TTS_VOICE", "").strip() or DEFAULT_VOICE


def state() -> Dict[str, Any]:
    voices = installed_voices()
    current = current_voice()
    label = next((v["label"] for v in voices if v["id"] == current), current)
    return {"current": current, "current_label": label, "voices": voices,
            "engine": "Kokoro-82M (local, ONNX)", "default": DEFAULT_VOICE}


def set_voice(voice: str, *, changed_by: str, channel: str) -> Dict[str, Any]:
    voice = str(voice or "").strip()
    allowed = {v["id"] for v in installed_voices()}
    if voice not in allowed:
        raise ValueError(f"'{voice}' is not an installed English voice. Choose one of: "
                         f"{', '.join(sorted(allowed))}.")
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    now = utc_now_iso()
    history = (data.get("history") or [])[-99:] + [
        {"voice": voice, "at": now, "by": changed_by, "channel": channel}]
    _path().parent.mkdir(parents=True, exist_ok=True)
    _path().write_text(json.dumps({"voice": voice, "changed_at": now, "changed_by": changed_by,
                                   "history": history}, indent=2), encoding="utf-8")
    return state()
