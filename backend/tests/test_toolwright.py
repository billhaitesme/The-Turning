"""Epoch XIII-D — the Toolwright: gap → find → quarantine → verify → biometric induction.

Candidates are declarative HTTP-read specs, never code; the runtime's generic executor is the
only hand that moves. Verification runs against the QUARANTINED artifact and makes one logged
fixture call through the breaker. Induction demands the operator's biometric; a plain approval
does not admit a tool. Denial deletes the quarantine. An inducted tool is a command like any
other — breaker-gated, logged, revivable at startup.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from services import network_breaker, tool_approval, toolwright
from services.adapters import spec_tool
from services.command_registry import get_command
from services.tool_registry import TOOL_REGISTRY


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_slate(monkeypatch):
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    # the fixture/network touchpoint is stubbed: the suite never reaches the real internet
    monkeypatch.setattr(spec_tool, "_http_get",
                        lambda url: (200, '{"current_weather": {"temperature": 11.5, "windspeed": 7}}'))
    yield
    network_breaker.set_breaker(False, changed_by="test", channel="test")
    TOOL_REGISTRY.pop("weather_now", None)


def _file_and_prepare(client, need="what is the weather and temperature outside"):
    filed = client.post("/system/toolwright/requests", json={"need": need, "why": "operator asked"})
    request_id = filed.json()["request"]["request_id"]
    prepared = client.post(f"/system/toolwright/requests/{request_id}/prepare")
    return request_id, prepared


def test_pipeline_finds_quarantines_and_verifies_from_the_catalog(client):
    request_id, prepared = _file_and_prepare(client)
    assert prepared.status_code == 200, prepared.text
    entry = prepared.json()["request"]
    assert entry["status"] == "verified"
    assert entry["candidate"]["name"] == "weather_now"
    assert entry["provenance"]["source"].startswith("catalog")
    assert entry["verification"]["verified"] is True
    assert any("fixture call OK" in c for c in entry["verification"]["checks"])
    assert (toolwright._quarantine_dir(request_id) / "spec.json").exists()
    # the fixture egress was logged like any other
    assert any(e["kind"] == "fetch" and "open-meteo" in e["target"]
               for e in network_breaker.list_fetch_log(limit=5))


def test_verification_requires_the_breaker(client):
    network_breaker.set_breaker(False, changed_by="test", channel="test")
    request_id, prepared = _file_and_prepare(client)
    assert prepared.status_code == 422
    assert "breaker is OFF" in prepared.json()["detail"]
    assert toolwright.get_request(request_id)["status"] == "failed"


def test_no_catalog_match_is_an_honest_refusal(client):
    filed = client.post("/system/toolwright/requests",
                        json={"need": "pilot a quantum flux capacitor", "why": ""})
    request_id = filed.json()["request"]["request_id"]
    r = client.post(f"/system/toolwright/requests/{request_id}/prepare")
    assert r.status_code == 422 and "No stocked-catalog candidate" in r.json()["detail"]


def test_induction_demands_the_biometric_and_then_the_tool_lives(client):
    request_id, _ = _file_and_prepare(client)
    # first induct press raises the approval
    r = client.post(f"/system/toolwright/requests/{request_id}/induct")
    assert r.status_code == 200 and r.json()["request"]["status"] == "awaiting_induction"
    induction = r.json()["request"]["induction"]
    # pressing again without any approval: refused
    assert client.post(f"/system/toolwright/requests/{request_id}/induct").status_code == 403
    # a PLAIN approval (no biometric) does not admit a tool
    tool_approval.approve_request(induction["request_id"], approved_by="operator")
    r = client.post(f"/system/toolwright/requests/{request_id}/induct")
    assert r.status_code == 403 and "BIOMETRIC" in r.json()["detail"]
    # the biometric confirmation releases it
    tool_approval.approve_request(induction["request_id"], approved_by="operator",
                                  confirmation="biometric")
    r = client.post(f"/system/toolwright/requests/{request_id}/induct")
    assert r.status_code == 200, r.text
    assert r.json()["request"]["status"] == "inducted"
    # the acquired tool is now a command like any other — and it executes through the runtime
    command = get_command("weather_now")
    assert command and command["gate"] == "direct" and command["category"] == "acquired"
    run = client.post("/system/commands/weather_now",
                      json={"arguments": {"latitude": 40.2, "longitude": -74.76}})
    assert run.status_code == 200, run.text
    output = run.json()["command"]["outcome"]["output"]
    assert "temperature" in output["output"]
    # the single-use approval is consumed: a second completion cannot replay it
    assert client.post(f"/system/toolwright/requests/{request_id}/induct").status_code == 422


def test_denial_deletes_the_quarantine(client):
    request_id, _ = _file_and_prepare(client)
    assert (toolwright._quarantine_dir(request_id) / "spec.json").exists()
    r = client.post(f"/system/toolwright/requests/{request_id}/deny")
    assert r.status_code == 200 and r.json()["request"]["status"] == "denied"
    assert not toolwright._quarantine_dir(request_id).exists()


def test_the_seat_can_file_a_gap_but_filing_is_not_having(client):
    from services import agent_loop
    result = agent_loop.execute_tool_call(
        "request_capability",
        {"need": "look up stock prices", "why": "operator asked for the market"},
        session_id="chat-test")
    assert result["status"] == "executed"
    outcome = result["outcome"]
    assert outcome["capability_request_id"].startswith("cap-")
    assert "not having" in outcome["note"]
    filed = toolwright.get_request(outcome["capability_request_id"])
    assert filed["status"] == "proposed" and filed["requested_by"] == "model:agent-seat"


def test_spec_contract_refuses_the_dangerous_shapes():
    base = {
        "name": "ok_tool", "title": "t", "description": "d", "tags": ["x"],
        "method": "GET", "url_template": "https://example.com/{q}",
        "params": [{"name": "q", "type": "text", "required": True}],
        "fixture": {"args": {"q": "a"}},
    }
    spec_tool.validate_spec(dict(base))  # sane baseline passes
    with pytest.raises(ValueError, match="GET-only"):
        spec_tool.validate_spec({**base, "method": "POST"})
    with pytest.raises(ValueError, match="https"):
        spec_tool.validate_spec({**base, "url_template": "http://example.com/{q}"})
    with pytest.raises(ValueError, match="exactly match"):
        spec_tool.validate_spec({**base, "url_template": "https://example.com/{other}"})
    with pytest.raises(ValueError):
        spec_tool.validate_spec({**base, "url_template": "https://localhost/{q}"})
    with pytest.raises(ValueError, match="fixture"):
        spec_tool.validate_spec({**base, "fixture": {"args": {}}})
