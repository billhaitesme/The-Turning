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
    # each test starts with an empty Toolwright store: an earlier test's inducted weather_now
    # otherwise collides with the next test's verification (order-dependent results)
    toolwright._store_path().unlink(missing_ok=True)
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


def test_an_unanswered_induction_prompt_can_be_raised_again(client):
    """Approvals live 5 minutes. An unanswered phone prompt used to strand the request in
    awaiting_induction forever (2026-11-06); the next press now raises a fresh approval."""
    request_id, _ = _file_and_prepare(client)
    first = client.post(f"/system/toolwright/requests/{request_id}/induct").json()["request"]["induction"]
    store = tool_approval.load_tool_approval_store()
    for approval in store["approvals"]:
        if approval["approval_id"] == first["approval_id"]:
            approval["expires_at"] = "2000-01-01T00:00:00+00:00"  # the prompt lapsed overnight
    tool_approval.save_tool_approval_store(store)
    assert toolwright.induction_approval_is_dead(toolwright.get_request(request_id))
    r = client.post(f"/system/toolwright/requests/{request_id}/induct")
    assert r.status_code == 200, r.text
    again = r.json()["request"]
    assert again["status"] == "awaiting_induction"
    assert again["induction"]["approval_id"] != first["approval_id"]
    # and the fresh approval completes the induction the normal way
    tool_approval.approve_request(again["induction"]["request_id"], approved_by="operator",
                                  confirmation="biometric")
    r = client.post(f"/system/toolwright/requests/{request_id}/induct")
    assert r.status_code == 200 and r.json()["request"]["status"] == "inducted"


def test_a_live_approval_is_not_re_raised(client):
    request_id, _ = _file_and_prepare(client)
    client.post(f"/system/toolwright/requests/{request_id}/induct")
    assert not toolwright.induction_approval_is_dead(toolwright.get_request(request_id))
    assert client.post(f"/system/toolwright/requests/{request_id}/induct").status_code == 403


def _induct(client, request_id):
    induction = client.post(f"/system/toolwright/requests/{request_id}/induct").json()["request"]["induction"]
    tool_approval.approve_request(induction["request_id"], approved_by="operator", confirmation="biometric")
    return client.post(f"/system/toolwright/requests/{request_id}/induct")


def test_an_inducted_tool_is_revised_only_through_a_new_biometric_induction(client, monkeypatch):
    """2026-11-06: weather_forecast reported km/h and the seat said m/s; there was no way to
    replace an inducted tool except hand-editing a live spec past the biometric."""
    first, _ = _file_and_prepare(client)
    assert _induct(client, first).json()["request"]["status"] == "inducted"
    old_url = toolwright.get_request(first)["candidate"]["url_template"]

    # the catalog's weather_now changes; a new request for it verifies as a REVISION
    revised = dict(next(c for c in toolwright._load_catalog() if c["name"] == "weather_now"))
    revised["url_template"] += "&wind_speed_unit=ms"
    monkeypatch.setattr(toolwright, "_load_catalog", lambda: [revised])
    second, prepared = _file_and_prepare(client)
    assert prepared.status_code == 200, prepared.text
    entry = prepared.json()["request"]
    assert entry["status"] == "verified" and entry["replaces"] == first
    assert any("revises Toolwright tool" in c for c in entry["verification"]["checks"])
    # until the operator's biometric, the OLD version is what runs
    assert TOOL_REGISTRY["weather_now"]["adapter"].spec["url_template"] == old_url

    assert _induct(client, second).json()["request"]["status"] == "inducted"
    assert toolwright.get_request(first)["status"] == "superseded"
    assert TOOL_REGISTRY["weather_now"]["adapter"].spec["url_template"].endswith("wind_speed_unit=ms")
    assert [s["url_template"] for s in toolwright.inducted_specs()] == [revised["url_template"]]
    # a superseded entry is history, not something to deny
    assert client.post(f"/system/toolwright/requests/{first}/deny").status_code == 422


def test_a_builtin_command_name_can_never_be_revised(client, monkeypatch):
    spec = dict(next(c for c in toolwright._load_catalog() if c["name"] == "weather_now"))
    spec["name"] = "check_capability_requests"  # a built-in command
    monkeypatch.setattr(toolwright, "_load_catalog", lambda: [spec])
    request_id, prepared = _file_and_prepare(client)
    assert prepared.status_code == 422 and "Name collision" in prepared.json()["detail"]


def test_every_catalog_entry_is_a_valid_unique_spec():
    from services.tool_registry import get_tool
    entries = toolwright._load_catalog()
    names = [e["name"] for e in entries]
    assert len(names) == len(set(names))
    for entry in entries:
        spec = spec_tool.validate_spec(entry)
        spec_tool.build_descriptor(spec)
        assert get_tool(spec["name"]) is None or spec["name"] in toolwright.inducted_specs(), spec["name"]


@pytest.mark.parametrize("need, why, expected", [
    # the seat's own words, filed 2026-11-06 in the first Toolwright workshop
    ("turn a place name into coordinates",
     "Bill needs this to input precise locations into weather and sea state tools", "geocode_place"),
    ("multi-day forecast with sunrise and sunset",
     "plan his watch duties and daily schedule; daylight hours vary in Norway", "weather_forecast"),
    ("current sea state data", "assess sea conditions: wave height, swell, and sea temperature",
     "marine_conditions"),
    ("USD to NOK exchange rate", "manage his finances during the move to Norway", "exchange_rate"),
    ("what is the weather and temperature outside", "operator asked", "weather_now"),
    ("what time is it in Oslo", "timezone for a call", "world_time"),
])
def test_find_routes_real_needs_to_the_right_shelf(need, why, expected):
    entry = toolwright.file_request(need, why, requested_by="test", session_id="test")
    assert toolwright.find_candidate(entry["request_id"])["candidate"]["name"] == expected


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


def test_the_seat_reads_where_its_requests_stand(client):
    from services import agent_loop
    request_id, _ = _file_and_prepare(client)
    result = agent_loop.execute_tool_call("check_capability_requests", {}, session_id="chat-test")
    assert result["status"] == "executed", result
    outcome = result["outcome"]
    mine = next(r for r in outcome["requests"] if r["capability_request_id"] == request_id)
    assert mine["status"] == "verified" and mine["matched_tool"] == "weather_now"
    assert outcome["installed_tools_usable_now"] == []
    assert {"geocode_place", "marine_conditions"} <= {s["name"] for s in outcome["shelf_NOT_installed"]}
    assert "never claim" in outcome["note"]
    # it is offered to the seat as a tool
    assert "check_capability_requests" in {s["function"]["name"] for s in agent_loop.build_tool_schemas()}


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
