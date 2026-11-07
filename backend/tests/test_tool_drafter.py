"""ADR 0027 slice 1b: the frontier drafts, the runtime tests, only a passing tool is filed.
Search, the frontier model and the network are all stubbed."""
from __future__ import annotations

import json

import pytest

from services import command_console, network_breaker, tool_drafter, toolwright
from services.adapters import spec_tool

V2 = {"name": "public_holidays", "title": "Public holidays", "description": "Holidays by country and year.",
      "url_template": "https://date.nager.at/Api/v2/PublicHolidays/{year}/{country}",
      "fixture_args": "year=2026; country=NO", "output_path": ""}
V3 = {**V2, "url_template": "https://date.nager.at/api/v3/PublicHolidays/{year}/{countryCode}",
      "fixture_args": "year=2026; countryCode=NO"}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    toolwright._store_path().unlink(missing_ok=True)
    network_breaker.set_breaker(True, changed_by="test", channel="test")

    def http(url):
        return (200, '[{"date": "2026-05-17"}]') if "/api/v3/" in url else (404, "not found")
    monkeypatch.setattr(spec_tool, "_http_get", http)
    yield
    network_breaker.set_breaker(False, changed_by="test", channel="test")


def fake_frontier(*drafts):
    prompts = []
    queue = list(drafts)

    def frontier(prompt):
        prompts.append(prompt)
        return "openai/gpt-oss-120b", "Here you go:\n" + json.dumps(queue.pop(0))
    frontier.prompts = prompts
    return frontier


def test_a_failed_draft_goes_back_with_the_reason_and_only_the_passing_one_is_filed():
    frontier = fake_frontier(V2, V3)
    out = tool_drafter.draft_tool("public holidays for a country and year", "trip planning",
                                  requested_by="model:agent-seat", session_id="s",
                                  search=lambda q: [{"title": "Nager.Date", "url": "https://date.nager.at", "snippet": "v3 API"}],
                                  frontier=frontier)
    assert out["attempts"] == 2 and out["url_template"] == V3["url_template"]
    assert "HTTP 404" in frontier.prompts[1] and "Api/v2" in frontier.prompts[1]  # it learned why
    requests = toolwright.list_requests()
    assert len(requests) == 1  # the failed draft was never filed
    entry = requests[0]
    assert entry["status"] == "found" and toolwright.is_authored(entry)
    assert entry["requested_by"].startswith("drafter:groq:openai/gpt-oss-120b")


def test_no_working_draft_files_nothing_and_says_why():
    with pytest.raises(ValueError) as caught:
        tool_drafter.draft_tool("public holidays", "", requested_by="model:agent-seat", session_id="s",
                                search=lambda q: [], frontier=fake_frontier(V2, V2, V2))
    assert "No working tool after 3 drafts" in str(caught.value) and "404" in str(caught.value)
    assert toolwright.list_requests() == []


def test_the_breaker_gates_drafting():
    network_breaker.set_breaker(False, changed_by="test", channel="test")
    with pytest.raises(command_console.CommandError) as caught:
        command_console.initiate_command("draft_tool", requested_by="model:agent-seat", channel="chat",
                                         arguments={"need": "public holidays"})
    assert caught.value.status == 422 and "breaker" in caught.value.detail.lower()


def test_a_taken_name_is_a_reason_to_redraft_not_a_late_failure():
    taken = {**V3, "name": "web_search"}  # a built-in tool
    frontier = fake_frontier(taken, V3)
    out = tool_drafter.draft_tool("public holidays", "", requested_by="m", session_id="s",
                                  search=lambda q: [], frontier=frontier)
    assert out["attempts"] == 2 and out["tool_name"] == "public_holidays"
    assert "already a built-in" in frontier.prompts[1]


def test_junk_from_the_drafter_is_a_reason_not_a_crash():
    frontier = fake_frontier()
    frontier_calls = iter(["no json here", json.dumps(V3)])

    def flaky(prompt):
        return "openai/gpt-oss-120b", next(frontier_calls)
    out = tool_drafter.draft_tool("public holidays", "", requested_by="m", session_id="s",
                                  search=lambda q: [], frontier=flaky)
    assert out["attempts"] == 2
