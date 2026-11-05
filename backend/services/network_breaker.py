"""The network breaker (ADR 0026, Epoch XIII-B) — the operator's standing switch for the senses.

Constitution article 7 ("tools, files, and network access only through explicit permissions")
made concrete: the runtime's network reads (web_search / web_fetch) execute only while this
breaker is ON. It is OFF by default, flipped only by an explicit recorded operator action from a
console — never by the model — and every flip is kept in the breaker's own history. Every search
and fetch that executes is appended to the fetch log (query/URL, time, bytes), browsable from
the consoles. Nothing silent.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from services.tool_contracts import utc_now_iso


def _breaker_path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "network_breaker.json"


def _fetch_log_path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "fetch_log.json"


def _load(path: Path, empty: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return deepcopy(empty)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deepcopy(empty)
    return data if isinstance(data, dict) else deepcopy(empty)


def _save(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


_EMPTY_BREAKER = {"version": 1, "on": False, "changed_at": None, "changed_by": None, "history": []}
_EMPTY_LOG = {"version": 1, "entries": []}


def breaker_state() -> Dict[str, Any]:
    state = _load(_breaker_path(), _EMPTY_BREAKER)
    state.setdefault("on", False)
    return state


def breaker_is_on() -> bool:
    return bool(breaker_state().get("on"))


def set_breaker(on: bool, *, changed_by: str, channel: str) -> Dict[str, Any]:
    """Flip the breaker — an explicit recorded operator action (Model-Lock style). The model has
    no path here: no registry command maps to this function by design."""
    state = breaker_state()
    now = utc_now_iso()
    state["on"] = bool(on)
    state["changed_at"] = now
    state["changed_by"] = changed_by
    history: List[Dict[str, Any]] = state.setdefault("history", [])
    history.append({"on": bool(on), "at": now, "by": changed_by, "channel": channel})
    if len(history) > 200:
        state["history"] = history[-200:]
    _save(_breaker_path(), state)
    return deepcopy(state)


class BreakerOpenError(ValueError):
    """Raised by the sense adapters when the breaker is OFF (the circuit is open). A ValueError
    on purpose: the console maps it to a 422 refusal — policy said no; nothing failed."""

    MESSAGE = ("The network breaker is OFF: internet reads are disabled by the operator's "
               "standing switch. Flipping it is the operator's recorded action, from a console — "
               "tell the operator; do not ask again until they flip it.")

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


def require_breaker_on() -> None:
    if not breaker_is_on():
        raise BreakerOpenError()


def record_fetch(kind: str, target: str, *, byte_count: int, ok: bool, detail: str = "") -> None:
    """Append one line to the fetch log. Every executed search and fetch lands here — the log is
    the breaker's receipt trail, browsable from the consoles."""
    log = _load(_fetch_log_path(), _EMPTY_LOG)
    entries: List[Dict[str, Any]] = log.setdefault("entries", [])
    entries.append({
        "kind": kind,                       # "search" | "fetch"
        "target": str(target)[:500],        # the query or URL
        "at": utc_now_iso(),
        "bytes": int(byte_count),
        "ok": bool(ok),
        "detail": str(detail)[:200],
    })
    if len(entries) > 500:
        log["entries"] = entries[-500:]
    _save(_fetch_log_path(), log)


def list_fetch_log(limit: int = 50) -> List[Dict[str, Any]]:
    entries = _load(_fetch_log_path(), _EMPTY_LOG).get("entries", [])
    return deepcopy(entries[-max(1, min(500, limit)):][::-1])
