"""The say-do gap and the guard's continue-retry (2026-11-06, Bill's 'write code' chat)."""
from __future__ import annotations

from services import agent_loop, escalation, repeat_guard


def seat_from(script, seen):
    script = iter(script)

    def seat(conversation, tools, model):
        seen.append([dict(m) for m in conversation])
        text, calls = next(script)
        for i in range(0, len(text), 9):
            yield {"type": "delta", "text": text[i:i + 9]}
        yield {"type": "message", "content": text, "tool_calls": calls}
    return seat


def run(user, script, monkeypatch, result=None):
    calls = []
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id, **kw: calls.append(name) or (result or {"status": "executed", "outcome": {"ok": True}}))
    seen = []
    events = list(agent_loop.iter_agent_loop(messages=[{"role": "user", "content": user}],
                                             model="t", session_id="c", seat_turn=seat_from(script, seen)))
    return events[-1], seen, calls


PROMISE = ("I understand. Let me examine my current capabilities. "
           "I'll start by checking my available tools.")


def test_an_empty_promise_is_sent_back_once_to_act(monkeypatch):
    final, seen, calls = run("status update?", [
        (PROMISE, []),                                             # promised, called nothing
        ("", [{"function": {"name": "describe_self", "arguments": {}}}]),  # now it acts
        ("I have a voice, a mic on the console, and four installed tools.", []),
    ], monkeypatch)
    assert calls == ["describe_self"]
    assert seen[1][-1]["content"] == escalation.PROMISE_NUDGE
    assert final["reply"].startswith(PROMISE) and final["reply"].endswith("four installed tools.")


def test_the_nudge_happens_once_per_turn(monkeypatch):
    final, seen, calls = run("status update?", [(PROMISE, []), ("I'll check that later.", [])],
                             monkeypatch)
    assert len(seen) == 2 and calls == []  # no third round: one nudge only


def test_a_promise_that_waits_on_the_operator_is_not_nudged(monkeypatch):
    final, seen, _ = run("run the health check", [
        ("The health check is awaiting your approval. When you're ready, I'll run it.", [])], monkeypatch)
    assert len(seen) == 1


LONG = ("The backend restarted cleanly at 11:29 and both phones reconnected through the tailnet "
        "within a minute. Four Toolwright tools are live: place lookup, forecast, sea state and "
        "the exchange rate. The forecast now reports wind in metres per second, and the console "
        "shows its buttons again after the fetch-log fix. Nothing is waiting on your approval.")


def test_a_caught_copy_after_shown_text_continues_instead_of_restarting(monkeypatch):
    # the round writes LONG (more than the hold-back, so its start is shown), then repeats it
    final, seen, _ = run("what changed?", [
        (LONG + " " + LONG, []),
        ("That covers everything.", []),
    ], monkeypatch)
    assert final["repeats_caught"] == 1
    retry_context = seen[1]
    assert retry_context[-1]["content"] == repeat_guard.CONTINUE_INSTRUCTION
    shown_before = retry_context[-2]["content"]
    assert retry_context[-2]["role"] == "assistant" and LONG.startswith(shown_before[:80])
    # the reply reads as one continuous answer: the shown part, then the continuation inline
    assert final["reply"] == shown_before + "That covers everything."
    assert final["reply"].count("The backend restarted cleanly") == 1


def test_let_me_try_again_is_a_promise():
    assert escalation.promises_action(
        "The web search timed out. Let me try again with a slightly different query.")


def test_when_every_word_is_withheld_the_runtime_says_what_happened(monkeypatch):
    authored = {"status": "executed", "outcome": {"capability_request_id": "cap-1", "tool_name": "public_holidays",
                                                  "note": "Authored and filed. Not usable yet."}}
    monkeypatch.setattr(agent_loop, "execute_tool_call", lambda name, args, session_id, **kw: authored)
    earlier = "The tool has been authored and filed. " + LONG
    script = iter([
        ("", [{"function": {"name": "author_tool", "arguments": {}}}]),
        (earlier, []),   # re-uses the previous reply's wording
        (earlier, []),   # and again
    ])

    def seat(conversation, tools, model):
        text, calls = next(script)
        for i in range(0, len(text), 9):
            yield {"type": "delta", "text": text[i:i + 9]}
        yield {"type": "message", "content": text, "tool_calls": calls}

    final = list(agent_loop.iter_agent_loop(
        messages=[{"role": "assistant", "content": earlier}, {"role": "user", "content": "fix it"}],
        model="t", session_id="c", seat_turn=seat))[-1]
    assert final["repeats_caught"] == 2
    assert "What happened this turn" in final["reply"]
    assert "author_tool: executed" in final["reply"] and "cap-1" in final["reply"]
