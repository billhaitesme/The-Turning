"""ADR 0027 slice 1: OMEGA authors a tool; the spec contract, the live fixture call and the
operator's biometric still decide. Network is stubbed (the suite never reaches the internet)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from services import command_console, network_breaker, tool_approval, toolwright
from services.adapters import spec_tool
from services.tool_registry import TOOL_REGISTRY

GOOD = {
    "need": "Norwegian public holidays for a year",
    "name": "public_holidays",
    "title": "Public holidays",
    "description": "Public holidays for a country and year, from the keyless Nager.Date API.",
    "url_template": "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}",
    "fixture_args": "year=2026; country=NO",
}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    toolwright._store_path().unlink(missing_ok=True)
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    monkeypatch.setattr(spec_tool, "_http_get",
                        lambda url: (200, '[{"date": "2026-05-17", "localName": "Grunnlovsdag"}]'))
    yield
    network_breaker.set_breaker(False, changed_by="test", channel="test")
    TOOL_REGISTRY.pop("public_holidays", None)


def author(**overrides):
    return command_console.initiate_command("author_tool", requested_by="model:agent-seat",
                                            channel="chat", arguments={**GOOD, **overrides})


def test_omega_authors_a_tool_and_only_the_operator_makes_it_live(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    filed = author()
    assert filed["status"] == "executed"
    request_id = filed["outcome"]["capability_request_id"]
    entry = toolwright.get_request(request_id)
    assert entry["status"] == "found" and toolwright.is_authored(entry)
    assert entry["candidate"]["params"] == [
        {"name": "year", "type": "text", "label": "year", "required": True},
        {"name": "country", "type": "text", "label": "country", "required": True}]
    assert entry["candidate"]["fixture"]["args"] == {"year": "2026", "country": "NO"}
    assert "public_holidays" not in TOOL_REGISTRY  # authoring is not having

    with TestClient(app) as client:
        prepared = client.post(f"/system/toolwright/requests/{request_id}/prepare")
        assert prepared.status_code == 200, prepared.text
        assert prepared.json()["request"]["status"] == "verified"  # live fixture call passed
        r = client.post(f"/system/toolwright/requests/{request_id}/induct")
        induction = r.json()["request"]["induction"]
        tool_approval.approve_request(induction["request_id"], approved_by="operator",
                                      confirmation="biometric")
        done = client.post(f"/system/toolwright/requests/{request_id}/induct")
        assert done.json()["request"]["status"] == "inducted"
    assert "public_holidays" in TOOL_REGISTRY


@pytest.mark.parametrize("override, reason", [
    ({"url_template": "http://date.nager.at/api/v3/PublicHolidays/{year}/{country}"}, "https"),
    ({"url_template": "https://127.0.0.1/api/{year}/{country}"}, "private"),
    ({"name": "Public Holidays!"}, "snake_case"),
    ({"fixture_args": "year=2026"}, "fixture"),
])
def test_the_contract_rejects_bad_specs_with_a_reason_the_author_can_use(override, reason):
    with pytest.raises(command_console.CommandError) as caught:
        author(**override)
    assert caught.value.status == 422
    assert "Spec rejected" in caught.value.detail and "Fix it" in caught.value.detail
    assert reason.lower() in caught.value.detail.lower()
    assert toolwright.list_requests() == []  # nothing filed


def test_a_failed_live_test_can_be_prepared_again(monkeypatch):
    request_id = author()["outcome"]["capability_request_id"]
    monkeypatch.setattr(spec_tool, "_http_get", lambda url: (404, "not found"))
    with TestClient(app) as client:
        assert client.post(f"/system/toolwright/requests/{request_id}/prepare").status_code == 422
        assert toolwright.get_request(request_id)["status"] == "failed"
        monkeypatch.setattr(spec_tool, "_http_get", lambda url: (200, '[{"date": "2026-05-17"}]'))
        again = client.post(f"/system/toolwright/requests/{request_id}/prepare")
        assert again.status_code == 200 and again.json()["request"]["status"] == "verified"


def test_an_address_that_already_failed_is_refused_with_the_reason(monkeypatch):
    request_id = author()["outcome"]["capability_request_id"]
    monkeypatch.setattr(spec_tool, "_http_get", lambda url: (404, "not found"))
    with TestClient(app) as client:
        client.post(f"/system/toolwright/requests/{request_id}/prepare")
    with pytest.raises(command_console.CommandError) as caught:
        author(name="public_holidays_two")   # same URL, new name
    assert "already failed its live test" in caught.value.detail and "404" in caught.value.detail
