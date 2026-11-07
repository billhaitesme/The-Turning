"""The Browser Hands bridge — OMEGA acting inside the operator's own browser tabs (ADR 0028).

Chrome 136+ and Edge refuse outside attachment to the everyday profile, and Firefox never
allowed it, so the only way into tabs the operator already has open is an extension, the way
Claude in Chrome works. The OMEGA extension (extension/) long-polls this bridge for jobs and
posts results back; no port is opened in the browser and nothing on the PC is exposed.

Trust, in order:
  1. Pairing token: generated once, stored locally, typed into the extension's options page.
     Every extension request carries it; a wrong token is a 401 and nothing more.
  2. The standing BROWSER HANDS switch (like the network breaker): OFF by default, flipped only
     by a recorded operator action from the console. Off = every job is refused.
  3. Per action: tabs / read / screenshot / open run under the switch alone; click and type act
     inside the operator's logged-in sessions and wait for the biometric approval.
  4. Everything is logged, and page text enters context as untrusted data, never instructions.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.tool_contracts import utc_now_iso

ACTIONS = ("list_tabs", "read_page", "open_url", "click", "type", "screenshot")
BROWSER_STALE_SECONDS = 60      # a browser not seen for this long counts as disconnected
JOB_TIMEOUT_SECONDS = 30.0      # how long a caller waits for the extension to finish a job
POLL_WAIT_MAX_SECONDS = 25.0    # long-poll ceiling (under the MV3 service-worker idle limit)
LOG_LIMIT = 200


class BridgeOff(ValueError):
    """The standing switch is OFF: a policy refusal, mapped to 422 by the console."""

    MESSAGE = ("BROWSER HANDS are OFF: acting in the operator's browser is disabled by their "
               "standing switch. Flipping it is the operator's recorded action from the desktop "
               "console; asking again does not flip it.")

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class NoBrowser(ValueError):
    """No paired browser has polled recently: the extension is not running or not paired."""


def _state_path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "browser_bridge.json"


def _load_state() -> Dict[str, Any]:
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("on", False)
    data.setdefault("history", [])
    data.setdefault("log", [])
    if not data.get("token"):
        data["token"] = secrets.token_urlsafe(24)
        _save_state(data)
    return data


def _save_state(data: Dict[str, Any]) -> None:
    _state_path().parent.mkdir(parents=True, exist_ok=True)
    _state_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def pairing_token() -> str:
    return str(_load_state()["token"])


def switch_is_on() -> bool:
    return bool(_load_state().get("on"))


def set_switch(on: bool, *, changed_by: str, channel: str) -> Dict[str, Any]:
    """Flip the standing switch: a recorded operator action. No registry command maps here."""
    data = _load_state()
    now = utc_now_iso()
    data["on"] = bool(on)
    data["changed_at"] = now
    data["changed_by"] = changed_by
    data["history"] = (data.get("history") or [])[-199:] + [
        {"on": bool(on), "at": now, "by": changed_by, "channel": channel}]
    _save_state(data)
    return switch_state()


def switch_state() -> Dict[str, Any]:
    data = _load_state()
    return {"on": bool(data.get("on")), "changed_at": data.get("changed_at"),
            "changed_by": data.get("changed_by"), "history": (data.get("history") or [])[-20:][::-1]}


def record(action: str, *, ok: bool, detail: str, browser: str = "") -> None:
    """Every job lands in the bridge's own log, browsable from the console."""
    data = _load_state()
    data["log"] = (data.get("log") or [])[-(LOG_LIMIT - 1):] + [
        {"at": utc_now_iso(), "action": action, "ok": ok, "detail": detail[:300], "browser": browser}]
    _save_state(data)


def recent_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(reversed((_load_state().get("log") or [])[-limit:]))


class BrowserBridge:
    """In-memory job exchange between callers (adapters) and the polling extension(s)."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._queue: List[Dict[str, Any]] = []
        self._inflight: Dict[str, Dict[str, Any]] = {}
        self._browsers: Dict[str, Dict[str, Any]] = {}

    # -- the extension side ------------------------------------------------------------
    def heartbeat(self, browser_id: str, info: Dict[str, Any]) -> None:
        with self._cond:
            self._browsers[browser_id] = {
                "browser": str(info.get("browser") or "unknown")[:40],
                "version": str(info.get("version") or "")[:40],
                "tabs": int(info.get("tabs") or 0),
                "last_seen": time.time(),
            }

    def _mine(self, browser_id: str, info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """The first queued job this browser may take: targeted at its name, or untargeted."""
        name = str(info.get("browser") or "unknown")
        for job in self._queue:
            if not job.get("browser") or job["browser"] == name:
                return job
        return None

    def next_job(self, browser_id: str, info: Dict[str, Any], *, wait: float) -> Optional[Dict[str, Any]]:
        """Long-poll: hand this browser its next job, or None after `wait` seconds. Jobs carry
        the browser they are for: with Chrome and Firefox both paired, Firefox answered
        list_tabs and Chrome then took the read_page jobs for Firefox's tab ids (first live run,
        2026-11-06)."""
        wait = max(0.0, min(POLL_WAIT_MAX_SECONDS, float(wait)))
        deadline = time.time() + wait
        with self._cond:
            self.heartbeat(browser_id, info)
            job = self._mine(browser_id, info)
            while job is None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self._cond.wait(remaining)
                job = self._mine(browser_id, info)
            self._queue.remove(job)
            job["claimed_by"] = browser_id
            job["claimed_at"] = time.time()
            self._inflight[job["job_id"]] = job
            return {"job_id": job["job_id"], "action": job["action"], "params": job["params"]}

    def complete(self, job_id: str, *, ok: bool, result: Any = None, error: str = "") -> bool:
        with self._cond:
            job = self._inflight.get(job_id)
            if job is None:
                return False
            job["done"] = True
            job["ok"] = bool(ok)
            job["result"] = result
            job["error"] = str(error or "")
            self._cond.notify_all()
            return True

    # -- the caller side ---------------------------------------------------------------
    def browsers(self) -> List[Dict[str, Any]]:
        now = time.time()
        with self._cond:
            out = []
            for browser_id, info in self._browsers.items():
                age = now - info["last_seen"]
                out.append({"browser_id": browser_id, "browser": info["browser"], "version": info["version"],
                            "tabs": info["tabs"], "seconds_since_seen": round(age, 1),
                            "connected": age <= BROWSER_STALE_SECONDS})
            return out

    def connected(self) -> bool:
        return any(b["connected"] for b in self.browsers())

    def connected_names(self) -> List[str]:
        """Connected browser names in preference order (chrome, edge, firefox, then others)."""
        order = {"chrome": 0, "edge": 1, "firefox": 2}
        names = sorted({b["browser"] for b in self.browsers() if b["connected"]},
                       key=lambda n: (order.get(n, 9), n))
        return names

    def call(self, action: str, params: Optional[Dict[str, Any]] = None, *, browser: Optional[str] = None,
             timeout: float = JOB_TIMEOUT_SECONDS) -> Any:
        """Run one action in the operator's browser and return its result. `browser` names the
        browser that must run it (chrome / firefox / edge); None = any. Raises BridgeOff,
        NoBrowser, or ValueError with the extension's own error text."""
        if action not in ACTIONS:
            raise ValueError(f"Unknown browser action {action!r}.")
        if not switch_is_on():
            record(action, ok=False, detail="refused: switch OFF")
            raise BridgeOff()
        names = self.connected_names()
        if not names:
            record(action, ok=False, detail="no paired browser connected")
            raise NoBrowser("No paired browser is connected: the OMEGA extension is not running, "
                            "not paired, or the browser is closed. The operator loads the extension "
                            "and pastes the pairing token from the console.")
        if browser and browser not in names:
            record(action, ok=False, detail=f"browser {browser} not connected", browser=browser)
            raise NoBrowser(f"The {browser} browser is not paired or not running; connected: {', '.join(names)}.")
        job = {"job_id": f"bj-{uuid.uuid4().hex[:12]}", "action": action, "params": dict(params or {}),
               "browser": browser or "", "created_at": time.time(), "done": False}
        with self._cond:
            self._queue.append(job)
            self._cond.notify_all()
            deadline = time.time() + timeout
            while not job["done"]:
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._queue[:] = [j for j in self._queue if j["job_id"] != job["job_id"]]
                    self._inflight.pop(job["job_id"], None)
                    record(action, ok=False, detail=f"timed out after {timeout:.0f}s", browser=job.get("claimed_by", ""))
                    raise ValueError(f"The browser did not answer within {timeout:.0f} s.")
                self._cond.wait(remaining)
            self._inflight.pop(job["job_id"], None)
        browser = str(job.get("claimed_by") or "")
        if not job["ok"]:
            record(action, ok=False, detail=job["error"] or "extension reported failure", browser=browser)
            raise ValueError(f"The browser reported: {job['error'] or 'failure'}")
        record(action, ok=True, detail=_summarise(action, job["result"]), browser=browser)
        return deepcopy(job["result"])


def list_all_tabs() -> List[Dict[str, Any]]:
    """list_tabs in EVERY connected browser, each tab tagged with its browser and given the
    composite id the other hands take ("firefox:16"). Tab ids collide across browsers."""
    if not switch_is_on():
        record("list_tabs", ok=False, detail="refused: switch OFF")
        raise BridgeOff()
    names = bridge.connected_names()
    if not names:
        record("list_tabs", ok=False, detail="no paired browser connected")
        raise NoBrowser("No paired browser is connected: the OMEGA extension is not running, "
                        "not paired, or the browser is closed.")
    tabs: List[Dict[str, Any]] = []
    errors: List[str] = []
    for name in names:
        try:
            for t in bridge.call("list_tabs", {}, browser=name) or []:
                if isinstance(t, dict):
                    tabs.append({**t, "browser": name, "tab": f"{name}:{t.get('id')}"})
        except ValueError as exc:
            errors.append(f"{name}: {exc}")
    if not tabs and errors:
        raise ValueError("; ".join(errors))
    return tabs


def split_tab(value: Any) -> tuple:
    """'firefox:16' -> ('firefox', 16). A bare integer is accepted only when one browser is
    connected (then it is that browser's)."""
    text = str(value or "").strip()
    if ":" in text:
        name, _, num = text.partition(":")
        name = name.strip().lower()
        if not num.strip().isdigit():
            raise ValueError(f"tab must look like 'chrome:12' (from browser_tabs); got {text!r}.")
        return name, int(num)
    if text.isdigit():
        names = bridge.connected_names()
        if len(names) == 1:
            return names[0], int(text)
        raise ValueError(f"tab must name its browser ('chrome:{text}' or 'firefox:{text}'): "
                         f"{len(names)} browsers are connected. Use the 'tab' value from browser_tabs.")
    raise ValueError("tab is required: call browser_tabs and use its 'tab' value (e.g. 'chrome:12').")


def _summarise(action: str, result: Any) -> str:
    if isinstance(result, dict):
        if action == "read_page":
            return f"{result.get('url', '')} ({len(str(result.get('text') or ''))} chars)"
        if action == "open_url":
            return str(result.get("url") or "")
        if action == "screenshot":
            return f"tab {result.get('tab_id')} image"
        return str(result.get("detail") or result.get("url") or "")[:120]
    if isinstance(result, list):
        return f"{len(result)} item(s)"
    return str(result)[:120]


bridge = BrowserBridge()
