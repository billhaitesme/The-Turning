"""A tool call written as TEXT (after the hop budget) reaches the operator as a plain note, not
raw JSON (first Browser Hands run, 2026-11-06)."""
from __future__ import annotations

from services import agent_loop


def test_default_hop_budget_is_six(monkeypatch):
    monkeypatch.delenv("AGENT_LOOP_MAX_HOPS", raising=False)
    assert agent_loop.max_hops() == 6


def test_a_leaked_tool_call_becomes_a_runtime_note(monkeypatch):
    monkeypatch.setenv("AGENT_LOOP_MAX_HOPS", "1")
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id, **kw: {"status": "executed", "outcome": {"tabs": []}})
    script = iter([
        ("", [{"function": {"name": "browser_tabs", "arguments": {}}}]),
        ('<tool_call>\n{"name": "browser_read", "arguments": {"tab":"chrome:13"}}\n</tool_call>', []),
    ])

    def seat(conversation, tools, model):
        text, calls = next(script)
        if text:
            yield {"type": "delta", "text": text}
        yield {"type": "message", "content": text, "tool_calls": calls}

    final = list(agent_loop.iter_agent_loop(messages=[{"role": "user", "content": "read my tab"}],
                                            model="t", session_id="c", seat_turn=seat))[-1]
    assert "tried to call browser_read" in final["reply"] and "budget" in final["reply"]
