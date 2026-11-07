"""Repeat guard (2026-11-06): the seat sent one identical reply six times in Bill's chat.

THE_REPEAT is that reply's shape (the joke itself swapped for a neutral one); the guard is about
copying, not content."""
from __future__ import annotations

import json

from services import agent_loop, repeat_guard

THE_REPEAT = (
    "I see, I need to improve my sense of humor. Let me try again with a more explicit joke:\n\n"
    "Why did the scarecrow win an award?  \nBecause he was outstanding in his field!  \n\n*laughs*  \n\n"
    "Okay, that was a bit of a setup. Let me try again with a more explicit one:\n\n"
    "Why did the scarecrow win an award?  \nBecause he was outstanding in his field!  \n\n*laughs*  \n\n"
    "Let me know if you want another!"
)
HISTORY = [
    {"role": "system", "content": "sys"},
    {"role": "user", "content": "tell me a joke"},
    {"role": "assistant", "content": THE_REPEAT},
    {"role": "user", "content": "That was terrible"},
    {"role": "assistant", "content": THE_REPEAT},
]


def seat_scripted(replies):
    """A fake seat streaming each scripted reply in small chunks; records what it was sent and
    whether its stream was closed early."""
    remaining = list(replies)

    def seat(conversation, tools, model):
        seat.calls.append([dict(m) for m in conversation])
        text = remaining.pop(0)

        def gen():
            try:
                for i in range(0, len(text), 7):
                    yield {"type": "delta", "text": text[i:i + 7]}
                yield {"type": "message", "content": text, "tool_calls": []}
            finally:
                seat.closed.append(True)
        return gen()

    seat.calls, seat.closed = [], []
    return seat


def streams_as_copy(guard, text, step=7):
    """What the loop does: judge the text after every streamed chunk."""
    return any(guard.copying(text[:end]) for end in range(step, len(text) + step, step))


def run(user, replies):
    seat = seat_scripted(replies)
    events = list(agent_loop.iter_agent_loop(
        messages=HISTORY + [{"role": "user", "content": user}], model="t", session_id="c", seat_turn=seat))
    streamed = "".join(e["text"] for e in events if e["event"] == "delta")
    return events[-1], streamed, seat


def test_a_verbatim_repeat_is_never_shown_and_the_retry_is():
    fresh = "Fair. That joke was weak and I kept recycling it. Here is a new one: I told my wife she " \
            "was drawing her eyebrows too high. She looked surprised."
    # (a plain retry, not "tell me a different joke": that is now a craft request the runtime
    # hands up the ladder before the seat speaks, 2026-11-07; the guard is what is under test)
    final, streamed, seat = run("Can you say something different this time?", [THE_REPEAT, fresh])
    assert final["repeats_caught"] == 1
    assert streamed == final["reply"] == fresh  # nothing of the copy reached the operator
    assert "scarecrow" not in streamed
    # the retry could not see the copied reply, and was told why
    retry_context = seat.calls[1]
    assert all(m["content"] != THE_REPEAT for m in retry_context)
    assert repeat_guard.WITHHELD in [m["content"] for m in retry_context]
    assert retry_context[-1]["content"] == repeat_guard.RETRY_INSTRUCTION


def test_a_fresh_opener_then_a_copy_is_caught_too():
    # the real 15:14 turn: a new first line, then the same joke block. A short opener is still
    # inside the held-back text when the copy is caught, so it goes with it: the retry answers
    # the whole message afresh. A long opener (past the hold) has already streamed and stays.
    opener = "The host status shows the system running smoothly at 2.7% CPU. "
    final, streamed, _ = run("I guess you're busy", [opener + THE_REPEAT, "Nothing else to add."])
    assert final["repeats_caught"] == 1
    assert streamed == final["reply"] == "Nothing else to add."
    long_opener = LONG_NEW + " "
    final, streamed, _ = run("I guess you're busy", [long_opener + THE_REPEAT, "Nothing else to add."])
    assert final["repeats_caught"] == 1 and "scarecrow" not in streamed
    assert streamed.startswith("The backend restarted") and streamed.endswith("Nothing else to add.")


def test_copying_twice_stops_with_a_plain_note():
    final, streamed, _ = run("Think deeper about what I asked", [THE_REPEAT, THE_REPEAT])
    assert final["repeats_caught"] == 2
    assert "scarecrow" not in streamed
    assert "Repeat guard" in final["reply"] and streamed == final["reply"]


def test_the_model_stream_is_closed_when_a_copy_is_caught():
    _, _, seat = run("again?", [THE_REPEAT, "New answer."])
    assert len(seat.closed) == 2  # the copying generation was stopped, not drained


def test_asking_for_a_repeat_is_honoured():
    final, streamed, _ = run("Repeat that word for word please", [THE_REPEAT])
    assert final["repeats_caught"] == 0 and streamed == THE_REPEAT


LONG_NEW = ("The backend restarted cleanly at 11:29 and both phones reconnected through the tailnet "
            "within a minute. Four Toolwright tools are live: place lookup, forecast, sea state and "
            "the exchange rate. The forecast now reports wind in metres per second, and the console "
            "shows its buttons again after the fetch-log fix. Nothing is waiting on your approval.")


def test_new_text_streams_whole_and_short_stock_replies_never_trip():
    final, streamed, _ = run("what changed?", [LONG_NEW])
    assert final["repeats_caught"] == 0 and streamed == LONG_NEW
    guard = repeat_guard.RepeatGuard(["Done.", "Approved."], "")
    assert not streams_as_copy(guard, "Done. " + LONG_NEW)


def test_markup_and_spacing_do_not_hide_a_copy():
    guard = repeat_guard.RepeatGuard([THE_REPEAT], "")
    disguised = THE_REPEAT.replace("*", "").replace("  \n", "\n").upper()
    assert guard.copying(disguised)


def test_the_word_swap_variant_is_a_copy_too():
    # live replay 2026-11-06: asked for "a different joke", the seat swapped three nouns
    swapped = (THE_REPEAT.replace("I see, I need to improve my sense of humor.", "Sure, a different one:")
               .replace("scarecrow", "tomato").replace("award", "medal").replace("field", "garden"))
    assert streams_as_copy(repeat_guard.RepeatGuard([THE_REPEAT], ""), swapped)


def test_a_block_said_twice_inside_one_reply_is_caught_with_no_history():
    # Bill's real joke reply (the same joke twice in one message) scored 0.89 when measured on
    # the live conversation. A short two-line joke duplicated once scores ~0.68, under the line:
    # the threshold was set from the real separation (repeats 0.89-1.00, normal <= 0.54), not
    # tuned to a fixture.
    guard = repeat_guard.RepeatGuard([], "status?")
    assert streams_as_copy(guard, LONG_NEW + "\n\nTo recap: " + LONG_NEW)
    assert not streams_as_copy(guard, LONG_NEW)


OSLO = ("The 3-day weather forecast for Oslo is as follows: November 6: Max temperature 3.2°C, Min "
        "temperature -0.1°C, Wind speed up to 7.2 m/s. November 7: Max temperature 2.7°C, Min "
        "temperature -0.6°C, Wind speed up to 7.6 m/s. November 8: Max temperature 4.0°C, Min "
        "temperature 0.3°C, Wind speed up to 6.1 m/s. Sunrise times are gradually getting later.")
BERGEN_FRESH = ("Here is the 3-day forecast for Bergen: November 6: Max temperature 9.3°C, Min "
                "temperature 3.0°C, Wind speed up to 4.1 m/s. November 7: Max temperature 9.3°C, Min "
                "temperature 5.5°C, Wind speed up to 2.6 m/s. November 8: Max temperature 7.9°C, Min "
                "temperature 3.5°C, Wind speed up to 2.8 m/s. Mild, with light winds.")


def test_same_template_new_numbers_is_not_a_copy_but_recycled_numbers_are():
    guard = repeat_guard.RepeatGuard([OSLO], "forecast for Bergen")
    assert not streams_as_copy(guard, BERGEN_FRESH)
    # the real morning failure: Oslo's numbers re-served under Bergen's name
    assert streams_as_copy(guard, OSLO.replace("Oslo", "Bergen"))


def test_a_fresh_fetch_may_repeat_the_earlier_answer(monkeypatch):
    """'What's the Oslo forecast again?' answered from a NEW tool call repeats the earlier reply
    honestly; the same reply with no tool call this turn is still a copy."""
    oslo_tool = {"status": "executed", "outcome": {"output": json.dumps(
        {"temperature_2m_max": [3.2, 2.7, 4.0], "temperature_2m_min": [-0.1, -0.6, 0.3],
         "wind_speed_10m_max": [7.2, 7.6, 6.1], "time": ["2026-11-06", "2026-11-07", "2026-11-08"]})}}
    monkeypatch.setattr(agent_loop, "execute_tool_call", lambda name, args, session_id: oslo_tool)
    history = [{"role": "user", "content": "Oslo forecast?"}, {"role": "assistant", "content": OSLO}]
    calls = iter([[{"function": {"name": "run_weather_forecast", "arguments": {}}}], []])
    texts = iter(["", OSLO])

    def seat(conversation, tools, model):
        text, tool_calls = next(texts), next(calls)
        if text:
            yield {"type": "delta", "text": text}
        yield {"type": "message", "content": text, "tool_calls": tool_calls}

    events = list(agent_loop.iter_agent_loop(
        messages=history + [{"role": "user", "content": "What's the Oslo forecast now?"}],
        model="t", session_id="c", seat_turn=seat))
    assert events[-1]["repeats_caught"] == 0 and events[-1]["reply"].startswith(OSLO)
    # with no fetch this turn, the identical text is a copy
    assert streams_as_copy(repeat_guard.RepeatGuard([OSLO], "What's the Oslo forecast now?"), OSLO)


def test_different_jokes_in_a_row_never_trip():
    jokes = ["Sure! Here's a joke about robots: Why don't robots ever get cold? Because they always "
             "wear sweaters, they're programmed to stay warm!",
             "Sure! Here's another one: Why did the robot get promoted? Because it was outstanding "
             "in its field! It had excellent circuits and a great attitude toward its work.",
             "Sure! Here's a better one: Why did the robot start a band? Because it had a great beat, "
             "it was programmed for rhythm and groove, and it never missed a single note."]
    for i, joke in enumerate(jokes):
        assert not streams_as_copy(repeat_guard.RepeatGuard(jokes[:i], "another one"), joke)


def test_a_repeat_across_tool_rounds_of_one_reply_is_caught(monkeypatch):
    """Live 2026-11-06: the seat wrote the voice list, called a tool, then wrote the whole list
    again in the next round; the reply reached Bill twice."""
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id: {"status": "executed", "outcome": {"ok": True}})
    script = iter([
        (LONG_NEW, [{"function": {"name": "check_capability_requests", "arguments": {}}}]),
        (LONG_NEW, []),                        # the same text again, next round
        ("Pick any of those and I'll switch.", []),  # the retry
    ])

    def seat(conversation, tools, model):
        text, calls = next(script)
        for i in range(0, len(text), 9):
            yield {"type": "delta", "text": text[i:i + 9]}
        yield {"type": "message", "content": text, "tool_calls": calls}

    events = list(agent_loop.iter_agent_loop(
        messages=[{"role": "user", "content": "what changed?"}], model="t", session_id="c", seat_turn=seat))
    final = events[-1]
    assert final["repeats_caught"] == 1
    assert final["reply"].count("The backend restarted cleanly") == 1
    assert final["reply"].endswith("Pick any of those and I'll switch.")
