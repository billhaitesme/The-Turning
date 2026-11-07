"""Self-questions are grounded before the seat speaks (2026-11-06: it claimed "I can write and
execute code" and only then called describe_self)."""
from __future__ import annotations

import pytest

from services import agent_loop, escalation

SELF = [
    "I need you to be able to write code. What can you do today, and what's missing? Examine yourself.",
    "is it possible to change your voice? if so, i'd like some options",
    "can you see the chat im currently having with you on the android?",
    "can you access my computer?",
    "who are you?",
    # Bill's voice chat: dodged instead of answering "no path" because this did not register
    "are there any other voices that we could download from somewhere that we could add?",
]
NOT_SELF = [
    "can you write me a prompt that will deliver that style of writing in a response?",
    "Tell me a joke about robots.",
    "What's the weather in Oslo for the next three days?",
]


@pytest.mark.parametrize("message", SELF)
def test_self_questions_are_recognised(message):
    assert escalation.self_question(message)


@pytest.mark.parametrize("message", NOT_SELF)
def test_tasks_and_chat_are_not(message):
    assert not escalation.self_question(message)


def test_describe_self_is_read_before_the_seat_speaks(monkeypatch):
    calls = []
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id, requested_by=agent_loop.AGENT_REQUESTED_BY:
                        calls.append((name, requested_by)) or
                        {"status": "executed", "outcome": {"limits": "You cannot change your own code."}})
    seen = []

    def seat(conversation, tools, model):
        seen.append([dict(m) for m in conversation])
        yield {"type": "delta", "text": "I cannot change my own code yet."}
        yield {"type": "message", "content": "I cannot change my own code yet.", "tool_calls": []}

    final = list(agent_loop.iter_agent_loop(messages=[{"role": "user", "content": SELF[0]}],
                                            model="t", session_id="c", seat_turn=seat))[-1]
    assert calls == [("describe_self", "runtime:escalation")]
    first = seen[0]
    assert first[-1]["content"] == escalation.SELF_NOTE
    assert "cannot change your own code" in first[-2]["content"]  # the facts, before any words
    assert final["reply"] == "I cannot change my own code yet."
