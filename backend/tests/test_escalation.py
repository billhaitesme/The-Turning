"""Runtime escalation (2026-11-06): the seat answered a probability puzzle inline and
contradicted itself; the runtime now sends clear multi-step problems up the ladder itself."""
from __future__ import annotations

import pytest

from services import agent_loop, escalation

GOES_UP = [
    # the live failure, verbatim
    "Two children, at least one is a boy born on a Tuesday. Boys and girls equally likely, all "
    "weekdays equally likely. What's the exact probability both are boys?",
    "A ship departs at 23:40 on Monday, steaming at 14 knots over 337 nautical miles with one "
    "2 h 15 min stop. What time does it arrive?",
    "How many times do the hour and minute hands overlap between 00:00 and 23:59? It's a puzzle.",
    "Can you put together a plan for moving my stuff to Norway in late January?",
    "If I save 400 a month at 4 percent interest, how much will I have after 3 years?",
]
STAYS = [
    "Tell me a joke about robots.",
    "That was terrible. Tell me a different one.",
    "Think deeper about what I asked, then respond.",  # the nudge from Bill's joke chat
    "Quickly: what are the odds it rains tomorrow in Bergen?",
    "What's the weather in Oslo for the next three days?",
    "How are you doing today, OMEGA?",
    "I have 2 dogs and 3 cats.",  # numbers, no question
    "What time is it?",  # too short
    "Status?",
    # the one real false positive found scanning Bill's 978 messages: an Ø2-02 body brief
    "Operating context, for this conversation only: you are speaking and acting through a body "
    "— a quadruped called Ø2-02. Walk speed 0.5 m/s; how long until you reach the door 3 m away?",
    "Here is a long pasted log to read, what time did the 2 errors happen? " + "x" * 1000,
]


@pytest.mark.parametrize("message", GOES_UP)
def test_clear_multi_step_problems_go_up(message):
    assert escalation.deep_task_reason(message)


@pytest.mark.parametrize("message", STAYS)
def test_chat_jokes_and_quick_asks_stay_with_the_seat(message):
    assert escalation.deep_task_reason(message) is None


def test_the_loop_runs_deep_think_first_and_the_seat_answers_with_it(monkeypatch):
    calls = []
    deep_answer = {"status": "executed", "outcome": {"rung": "local", "answer": "…long reasoning… = 13/27"}}

    def fake_execute(name, args, session_id, requested_by=agent_loop.AGENT_REQUESTED_BY):
        calls.append((name, args))
        assert requested_by == "runtime:escalation"  # the audit log says who really asked
        return deep_answer

    monkeypatch.setattr(agent_loop, "execute_tool_call", fake_execute)
    seen = {}

    def seat(conversation, tools, model):
        seen["conversation"] = [dict(m) for m in conversation]
        yield {"type": "delta", "text": "It's 13/27."}
        yield {"type": "message", "content": "It's 13/27.", "tool_calls": []}

    events = list(agent_loop.iter_agent_loop(
        messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": GOES_UP[0]}],
        model="t", session_id="c", seat_turn=seat))
    assert calls == [("deep_think", {"task": GOES_UP[0], "rung": "local"})]
    kinds = [e["event"] for e in events]
    assert kinds.index("tool_call") < kinds.index("tool_result") < kinds.index("final")
    final = events[-1]
    assert final["reply"].startswith(escalation.ANNOUNCE) and final["reply"].endswith("It's 13/27.")
    assert final["hops"][0] == {"tool": "deep_think", "status": "executed"}
    roles = [m["role"] for m in seen["conversation"]]
    assert roles[-3:] == ["assistant", "tool", "system"]  # the seat sees the call, the result, the note
    assert "13/27" in seen["conversation"][-2]["content"]
    assert final["unverified_numbers"] == []  # 13/27 is grounded in the deep result


def test_ordinary_chat_never_calls_deep_think(monkeypatch):
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda *a, **k: pytest.fail("deep_think must not run for chat"))

    def seat(conversation, tools, model):
        yield {"type": "message", "content": "Ha.", "tool_calls": []}

    for chat in ("How are you doing today, OMEGA?", "What's the weather in Oslo for the next three days?"):
        list(agent_loop.iter_agent_loop(messages=[{"role": "user", "content": chat}],
                                        model="t", session_id="c", seat_turn=seat))


# ---------------------------------------------------------------- craft requests (2026-11-07)
CRAFT = [
    "Tell me a joke about robots.",
    "can you please tell me a joke about a vagina?",
    "write me a limerick about a hexapod called Gary",
    "i want you to be able to tell me a joke in the style of george carlin or richard pryor, and it make sense",
    "give me a toast for my brother's wedding, two sentences",
    "Hit me with a one-liner.",
    "Compose a haiku about the night watch.",
]
NOT_CRAFT = [
    "how is that a joke?",
    "explain why thats funny.",
    "since when is \"denominator\" a slang term for \"vagina?\" where are you getting your information?",
    "What's the weather in Oslo for the next three days?",
    "who wrote the poem Invictus?",
    "what is the history of stand-up comedy?",
    "another one",                     # a retry with no craft hand-off before it: plain chat
    GOES_UP[0],                        # the puzzle stays a deep task
]


@pytest.mark.parametrize("message", CRAFT)
def test_creative_requests_are_craft(message):
    assert escalation.craft_reason(message) == "creative piece requested"
    assert escalation.deep_task_reason(message) is None   # jokes never go to the slow local rung


@pytest.mark.parametrize("message", NOT_CRAFT)
def test_questions_and_chat_are_not_craft(message):
    assert escalation.craft_reason(message) is None


def test_a_retry_is_craft_only_after_a_craft_hand_off():
    handed_off = escalation.CRAFT_ANNOUNCE + "\n\nWhy did the robot ... because it had hard drive."
    assert escalation.craft_reason("another one", handed_off) == "retry of a creative piece"
    assert escalation.craft_reason("that was terrible, try again", handed_off)
    assert escalation.craft_reason("go ahead", handed_off)
    assert escalation.craft_reason("another one", "Ha, fair. What next?") is None
    assert escalation.craft_reason("what time is it?", handed_off) is None


def test_the_loop_has_the_frontier_write_the_piece_and_the_seat_delivers_it(monkeypatch):
    """The joke conversation: the seat wrote jokes it could not write and lectures it was not
    asked for. Now the runtime asks the frontier rung to WRITE, and tells the seat to deliver."""
    from services import network_breaker
    calls = []
    joke = "I used to think the brain was the most important organ. Then I thought, look what's telling me that."

    def fake_execute(name, args, session_id, requested_by=agent_loop.AGENT_REQUESTED_BY):
        calls.append((name, args, requested_by))
        return {"status": "executed", "outcome": {"rung": args["rung"], "answer": joke}}

    monkeypatch.setattr(agent_loop, "execute_tool_call", fake_execute)
    seen = {}

    def seat(conversation, tools, model):
        seen["conversation"] = [dict(m) for m in conversation]
        yield {"type": "delta", "text": joke}
        yield {"type": "message", "content": joke, "tool_calls": []}

    network_breaker.set_breaker(True, changed_by="test", channel="test")
    try:
        events = list(agent_loop.iter_agent_loop(
            messages=[{"role": "user", "content": CRAFT[0]}], model="t", session_id="c", seat_turn=seat))
    finally:
        network_breaker.set_breaker(False, changed_by="test", channel="test")
    name, args, who = calls[0]
    assert name == "deep_think" and who == "runtime:escalation" and args["rung"] == "frontier"
    assert args["task"].startswith("WRITE the piece") and CRAFT[0] in args["task"]
    final = events[-1]
    assert final["reply"].startswith(escalation.CRAFT_ANNOUNCE) and final["reply"].endswith(joke)
    assert seen["conversation"][-1]["role"] == "system" and "Deliver that text" in seen["conversation"][-1]["content"]
    assert "Learning check" not in final["reply"]

    # breaker OFF: the piece still gets written, by the local deep rung
    calls.clear()
    list(agent_loop.iter_agent_loop(messages=[{"role": "user", "content": CRAFT[2]}],
                                    model="t", session_id="c", seat_turn=seat))
    assert calls[0][1]["rung"] == "local"
