"""Browser Hands routes (ADR 0028).

The extension side (token-authenticated): hello, next (long-poll for a job), result.
The console side (local): status, the standing switch, the pairing token.
"""
from __future__ import annotations

import hmac
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services import browser_bridge
from services.browser_bridge import bridge

router = APIRouter(prefix="/browser", tags=["browser"])


def _require_token(token: Optional[str]) -> None:
    expected = browser_bridge.pairing_token()
    if not token or not hmac.compare_digest(str(token), expected):
        raise HTTPException(status_code=401, detail="Bad or missing pairing token.")


class PollBody(BaseModel):
    browser_id: str = Field(..., min_length=1, max_length=80)
    browser: str = Field(default="unknown", max_length=40)
    version: str = Field(default="", max_length=40)
    tabs: int = Field(default=0, ge=0, le=10_000)
    wait: float = Field(default=browser_bridge.POLL_WAIT_MAX_SECONDS, ge=0, le=browser_bridge.POLL_WAIT_MAX_SECONDS)


@router.post("/hello")
def hello(body: PollBody, x_browser_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _require_token(x_browser_token)
    bridge.heartbeat(body.browser_id, body.model_dump())
    return {"paired": True, "hands_on": browser_bridge.switch_is_on(), "actions": list(browser_bridge.ACTIONS)}


@router.post("/next")
def next_job(body: PollBody, x_browser_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Long-poll: the extension asks for the next job and waits up to `wait` seconds."""
    _require_token(x_browser_token)
    job = bridge.next_job(body.browser_id, body.model_dump(), wait=body.wait)
    return {"job": job, "hands_on": browser_bridge.switch_is_on()}


class ResultBody(BaseModel):
    job_id: str = Field(..., min_length=1, max_length=40)
    ok: bool
    result: Any = None
    error: str = Field(default="", max_length=2000)


@router.post("/result")
def post_result(body: ResultBody, x_browser_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _require_token(x_browser_token)
    accepted = bridge.complete(body.job_id, ok=body.ok, result=body.result, error=body.error)
    return {"accepted": accepted}


@router.get("/status")
def status() -> Dict[str, Any]:
    return {"switch": browser_bridge.switch_state(), "browsers": bridge.browsers(),
            "connected": bridge.connected(), "log": browser_bridge.recent_log(12)}


@router.get("/pairing")
def pairing() -> Dict[str, Any]:
    """The pairing token for the extension's options page. Local console only."""
    return {"token": browser_bridge.pairing_token(), "backend": "http://127.0.0.1:8001"}


class SwitchBody(BaseModel):
    on: bool
    changed_by: str = Field(default="operator", max_length=120)


@router.post("/switch")
def flip_switch(body: SwitchBody) -> Dict[str, Any]:
    """The standing BROWSER HANDS switch: a recorded operator action from a console."""
    return browser_bridge.set_switch(body.on, changed_by=f"operator:{body.changed_by}", channel="desktop")
