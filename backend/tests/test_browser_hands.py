"""Browser Hands (ADR 0028): pairing token, the standing switch, the job exchange, the hands'
contracts and gates, and the extension's manifest. The browser is played by the test."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app
from services import browser_bridge, command_console
from services.adapters import browser_hands
from services.browser_bridge import bridge
from services.command_registry import get_command
from services.tool_registry import TOOL_REGISTRY

EXT = Path(__file__).resolve().parents[2] / "extension"


@pytest.fixture(autouse=True)
def clean():
    browser_bridge._state_path().unlink(missing_ok=True)
    with bridge._cond:
        bridge._queue.clear()
        bridge._inflight.clear()
        bridge._browsers.clear()
    yield
    browser_bridge._state_path().unlink(missing_ok=True)


def headers():
    return {"X-Browser-Token": browser_bridge.pairing_token()}


def poll(client, wait=0.0):
    return client.post("/browser/next", json={"browser_id": "test-chrome", "browser": "chrome",
                                              "version": "156", "tabs": 3, "wait": wait}, headers=headers())


def test_token_is_generated_once_and_required():
    first = browser_bridge.pairing_token()
    assert len(first) >= 24 and browser_bridge.pairing_token() == first
    client = TestClient(app)
    assert client.post("/browser/hello", json={"browser_id": "x"}).status_code == 401
    assert client.post("/browser/hello", json={"browser_id": "x"}, headers={"X-Browser-Token": "nope"}).status_code == 401
    ok = client.post("/browser/hello", json={"browser_id": "x", "browser": "chrome"}, headers=headers())
    assert ok.status_code == 200 and ok.json()["paired"] is True and ok.json()["hands_on"] is False


def test_the_switch_is_off_by_default_and_refuses_every_job():
    assert browser_bridge.switch_is_on() is False
    with pytest.raises(browser_bridge.BridgeOff):
        bridge.call("list_tabs")
    assert browser_bridge.recent_log(1)[0]["detail"].startswith("refused: switch OFF")


def test_no_browser_is_a_plain_refusal():
    browser_bridge.set_switch(True, changed_by="test", channel="test")
    with pytest.raises(browser_bridge.NoBrowser, match="not running, not paired"):
        bridge.call("list_tabs")


def test_a_job_round_trips_through_the_extension():
    browser_bridge.set_switch(True, changed_by="test", channel="test")
    client = TestClient(app)
    assert poll(client).json()["job"] is None          # nothing queued yet, and now the browser is seen
    results = {}

    def caller():
        results["tabs"] = bridge.call("list_tabs", timeout=5)
    t = threading.Thread(target=caller)
    t.start()
    job = None
    for _ in range(50):
        job = poll(client, wait=0.2).json()["job"]
        if job:
            break
    assert job and job["action"] == "list_tabs"
    done = client.post("/browser/result", json={"job_id": job["job_id"], "ok": True,
                                                "result": [{"id": 7, "title": "Weather", "url": "https://yr.no", "active": True}]},
                       headers=headers())
    assert done.json()["accepted"] is True
    t.join(5)
    assert results["tabs"][0]["title"] == "Weather"
    log = browser_bridge.recent_log(1)[0]
    assert log["ok"] is True and log["action"] == "list_tabs" and log["browser"] == "test-chrome"
    status = client.get("/browser/status").json()
    assert status["connected"] is True and status["browsers"][0]["browser"] == "chrome"


def test_an_extension_error_and_a_timeout_are_reported_not_hung():
    browser_bridge.set_switch(True, changed_by="test", channel="test")
    client = TestClient(app)
    poll(client)
    out = {}
    t = threading.Thread(target=lambda: out.update(err=_catch(lambda: bridge.call("read_page", {"tab_id": 1}, timeout=5))))
    t.start()
    job = None
    for _ in range(50):
        job = poll(client, wait=0.2).json()["job"]
        if job:
            break
    client.post("/browser/result", json={"job_id": job["job_id"], "ok": False, "error": "cannot run in tab 1: chrome:// page"},
                headers=headers())
    t.join(5)
    assert "cannot run in tab 1" in str(out["err"])
    with pytest.raises(ValueError, match="did not answer within"):
        bridge.call("list_tabs", timeout=0.3)


def _catch(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return exc


def test_hands_are_registered_with_the_right_gates():
    for name in ("browser_tabs", "browser_read", "browser_screenshot", "browser_open"):
        cmd = get_command(name)
        assert cmd and cmd["gate"] == "direct" and cmd["category"] == "browser", name
        assert TOOL_REGISTRY[name]["descriptor"]["side_effects"] == []
    for name in ("browser_click", "browser_type"):
        cmd = get_command(name)
        assert cmd and cmd["gate"] == "approval", name
        assert TOOL_REGISTRY[name]["descriptor"]["requires_approval"] is True


def test_direct_hands_run_through_the_console_and_off_switch_is_a_422(monkeypatch):
    with pytest.raises(command_console.CommandError) as caught:
        command_console.initiate_command("browser_tabs", requested_by="model:agent-seat", channel="chat")
    assert caught.value.status == 422 and "BROWSER HANDS are OFF" in caught.value.detail
    browser_bridge.set_switch(True, changed_by="test", channel="test")
    monkeypatch.setattr(browser_hands, "bridge", type("B", (), {"call": staticmethod(
        lambda action, params=None, **kw: [{"id": 3, "title": "Docs", "url": "https://x.y", "active": False}])})())
    entry = command_console.initiate_command("browser_tabs", requested_by="model:agent-seat", channel="chat")
    assert entry["status"] == "executed" and entry["outcome"]["output"]["tabs"][0]["tab_id"] == 3


def test_open_requires_http_and_read_requires_a_tab():
    with pytest.raises(ValueError, match="http"):
        browser_hands.BrowserOpenAdapter().validate_arguments({"url": "file:///etc/passwd"})
    with pytest.raises(ValueError, match="tab_id"):
        browser_hands.BrowserReadAdapter().validate_arguments({})
    assert browser_hands.BrowserOpenAdapter().validate_arguments({"url": "https://yr.no", "tab_id": "12"}) == {
        "url": "https://yr.no", "tab_id": 12}


def test_screenshot_lands_in_the_image_store(monkeypatch):
    tiny = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    monkeypatch.setattr(browser_hands, "bridge", type("B", (), {"call": staticmethod(
        lambda action, params=None, **kw: {"tab_id": 4, "image": tiny})})())
    out = browser_hands.BrowserScreenshotAdapter().execute({"tab_id": 4})
    assert out["image_id"] and "look_at_image" in out["note"]


def test_the_extension_manifest_is_cross_browser_and_names_every_action():
    manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert "service_worker" in manifest["background"] and "scripts" in manifest["background"]  # Chrome/Edge + Firefox
    assert "gecko" in manifest["browser_specific_settings"]
    assert {"tabs", "scripting", "storage", "alarms"} <= set(manifest["permissions"])
    background = (EXT / "background.js").read_text(encoding="utf-8")
    for action in browser_bridge.ACTIONS:
        assert f'case "{action}"' in background, action
    assert "/browser/next" in background and "/browser/result" in background
