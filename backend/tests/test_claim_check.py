"""Tool-claim check (2026-11-06): the seat reported "the draft tool couldn't find a working API"
in a turn where no tool ran at all."""
from __future__ import annotations

import json

import pytest

from services import agent_loop, claim_check, tool_drafter, toolwright, network_breaker

REGISTERED = ["draft_tool", "author_tool", "list_voices", "set_voice", "web_search", "describe_self"]
FABRICATED = ("It seems there was an issue integrating the new voice. The draft tool couldn't find "
              "a working API to fetch the voice. Let's try a different approach.")
OFFER = ("If you'd like to add more voices, you can use the draft_tool or author_tool functions "
         "to integrate new voices from external sources. Would you like to explore that?")


def test_the_fabricated_failure_is_caught_and_the_offer_is_not():
    assert [n for n, _ in claim_check.claimed_but_not_run(FABRICATED, REGISTERED, [])] == ["draft_tool"]
    assert claim_check.claimed_but_not_run(OFFER, REGISTERED, []) == []


def test_a_claim_about_a_tool_that_did_run_is_fine():
    assert claim_check.claimed_but_not_run(FABRICATED, REGISTERED, ["draft_tool"]) == []
    assert claim_check.claimed_but_not_run("I've switched to George; set_voice ran fine.",
                                           REGISTERED, ["set_voice"]) == []


def test_the_loop_appends_the_note_and_names_what_actually_ran(monkeypatch):
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id, **kw: {"status": "executed", "outcome": {"voices": []}})
    script = iter([("", [{"function": {"name": "list_voices", "arguments": {}}}]), (FABRICATED, [])])

    def seat(conversation, tools, model):
        text, calls = next(script)
        if text:
            yield {"type": "delta", "text": text}
        yield {"type": "message", "content": text, "tool_calls": calls}

    final = list(agent_loop.iter_agent_loop(messages=[{"role": "user", "content": "add a voice"}],
                                            model="t", session_id="c", seat_turn=seat))[-1]
    assert final["unverified_claims"] == ["draft_tool"]
    assert "Tool-claim check" in final["reply"] and "list_voices ran" in final["reply"]


# ---------------------------------------------------------------- study and learning claims (2026-11-07)
STUDIED = ("I've studied the Director Mel Brooks and his style of comedic storytelling. His style is "
           "characterized by a mix of slapstick, parody, and irreverent humor.")
ANALYSED = "I've analyzed examples of jokes in the style of George Carlin and Richard Pryor."
PROMISE = "Correct. I will learn from that and ensure my responses are unique in the future."


def test_study_claimed_after_a_search_only_is_noted():
    note = claim_check.learning_note(STUDIED, ["web_search"])
    assert "Learning check" in note and "web_search ran 1 time" in note and "titles and snippets only" in note
    assert "2 times" in claim_check.learning_note(ANALYSED, ["web_search", "web_search"])
    assert "no tool ran" in claim_check.learning_note(STUDIED, [])


def test_study_after_a_real_read_is_not_noted():
    assert claim_check.learning_note("I've read through the page you gave me; it says ...", ["browser_read"]) == ""
    assert claim_check.learning_note("I've reviewed the article.", ["web_search", "own_browser_read"]) == ""
    assert claim_check.learning_note("Here is the forecast for Oslo.", ["weather_forecast"]) == ""


def test_a_promise_to_learn_is_always_noted():
    note = claim_check.learning_note(PROMISE, [])
    assert "cannot learn or change within a conversation" in note
    assert "I'll keep that in mind." in "I'll keep that in mind." and claim_check.learning_note("I'll keep that in mind.", [])
    assert claim_check.learning_note("You're right, that wasn't funny.", []) == ""


def test_the_loop_appends_the_learning_note(monkeypatch):
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id, **kw: {"status": "executed", "outcome": {"results": []}})
    script = iter([("", [{"function": {"name": "web_search", "arguments": {"query": "mel brooks"}}}]), (STUDIED, [])])

    def seat(conversation, tools, model):
        text, calls = next(script)
        if text:
            yield {"type": "delta", "text": text}
        yield {"type": "message", "content": text, "tool_calls": calls}

    final = list(agent_loop.iter_agent_loop(messages=[{"role": "user", "content": "study Mel Brooks"}],
                                            model="t", session_id="c", seat_turn=seat))[-1]
    assert final["reply"].startswith(STUDIED) and "Learning check" in final["reply"]
    assert "web_search ran 1 time" in final["reply"]


@pytest.fixture
def breaker_on():
    toolwright._store_path().unlink(missing_ok=True)
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    yield
    network_breaker.set_breaker(False, changed_by="test", channel="test")


def test_the_drafter_refuses_a_non_lookup_in_one_call(breaker_on):
    calls = []

    def frontier(prompt):
        calls.append(prompt)
        return "openai/gpt-oss-120b", json.dumps({"refuse": "voices are not a JSON web lookup"})

    with pytest.raises(ValueError) as caught:
        tool_drafter.draft_tool("add a new voice to the available choices", "",
                                requested_by="m", session_id="s", search=lambda q: [], frontier=frontier)
    assert len(calls) == 1  # no retries
    assert "Not a data lookup" in str(caught.value) and "no path exists" in str(caught.value)
    assert toolwright.list_requests() == []
