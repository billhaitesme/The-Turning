"""Per-item field selection in the spec contract (2026-11-06): a year of public holidays overran
the 3000-char output cap and the later months were cut off."""
from __future__ import annotations

import json

import pytest

from services import network_breaker, tool_drafter, toolwright
from services.adapters import spec_tool

HOLIDAY = {"date": "2026-01-01", "localName": "Nyttårsdag", "name": "New Year's Day",
           "countryCode": "NO", "fixed": False, "global": True, "counties": None,
           "launchYear": None, "types": ["Public"]}
# 24 distinct holidays (two per month), so the last one only appears if nothing was cut off
YEAR = [dict(HOLIDAY, date=f"2026-{(i - 1) % 12 + 1:02d}-{15 if i <= 12 else 28}", name=f"Holiday {i}")
        for i in range(1, 25)]
BASE = {"name": "public_holidays", "title": "Public holidays", "description": "Holidays by year.",
        "method": "GET", "url_template": "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}",
        "params": [{"name": "year", "type": "text", "required": True},
                   {"name": "country", "type": "text", "required": True}],
        "tags": ["holidays"], "fixture": {"args": {"year": "2026", "country": "NO"}},
        "max_output_chars": 3000}


@pytest.fixture(autouse=True)
def live(monkeypatch):
    toolwright._store_path().unlink(missing_ok=True)
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    monkeypatch.setattr(spec_tool, "_http_get", lambda url: (200, json.dumps(YEAR)))
    yield
    network_breaker.set_breaker(False, changed_by="test", channel="test")


def run(spec):
    return spec_tool.SpecToolAdapter(spec).execute({"year": "2026", "country": "NO"})


def test_without_field_selection_a_year_is_cut_off():
    out = run(BASE)
    assert out["truncated"] is True and "Holiday 24" not in out["output"]


def test_with_field_selection_the_whole_year_fits():
    out = run({**BASE, "output_fields": "date, localName, name"})
    assert out["truncated"] is False
    items = json.loads(out["output"])
    assert len(items) == 24 and items[-1] == {"date": "2026-12-28", "localName": "Nyttårsdag",
                                              "name": "Holiday 24"}


def test_fields_that_match_nothing_are_an_error_naming_the_real_fields():
    out = run({**BASE, "output_fields": ["when", "title"]})
    assert "none of output_fields" in out["error"] and "'localName'" in out["error"]


@pytest.mark.parametrize("bad", [["a b"], ["x"] * 21, "date; DROP TABLE"])
def test_the_contract_checks_field_names(bad):
    with pytest.raises(ValueError):
        spec_tool.validate_spec({**BASE, "output_fields": bad})


def test_old_specs_without_fields_are_unchanged():
    assert spec_tool.validate_spec(BASE)["output_fields"] == []


def test_the_drafter_will_not_file_a_cut_off_tool():
    full = {"name": "public_holidays", "title": "Public holidays", "description": "Holidays.",
            "url_template": BASE["url_template"], "fixture_args": "year=2026; country=NO",
            "output_path": "", "output_fields": ""}
    # the second draft answers a JSON list, not the requested comma string: both must work
    drafts = iter([full, {**full, "output_fields": ["date", "localName", "name"]}])
    prompts = []

    def frontier(prompt):
        prompts.append(prompt)
        return "openai/gpt-oss-120b", json.dumps(next(drafts))

    out = tool_drafter.draft_tool("public holidays", "", requested_by="m", session_id="s",
                                  search=lambda q: [], frontier=frontier)
    assert out["attempts"] == 2
    assert "cut off at 3000 characters" in prompts[1]
    spec = toolwright.get_request(out["capability_request_id"])["candidate"]
    assert spec["output_fields"] == ["date", "localName", "name"]
