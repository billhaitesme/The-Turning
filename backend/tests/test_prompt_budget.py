"""Prompt budget (2026-11-06): each history turn reaches the seat exactly once.

The system message used to carry a "Recent history" block AND the same turns were sent as chat
messages, doubling history tokens; prompts reached 8058 of the 8192-token window, and Ollama
truncates from the front, where the constitution and identity live.
"""
from __future__ import annotations

import app as runtime

MARKER = "the-zebra-on-the-foredeck-7731"


def test_history_is_sent_once_as_real_turns_not_twice():
    history = [
        {"role": "user", "content": f"earlier question about {MARKER}"},
        {"role": "assistant", "content": "an earlier answer"},
    ]
    messages = runtime.build_ollama_messages(
        history=history, user_message="next question", user_profile={"preferences": {}},
        memories=[], web_results=[], conversation_id=None)
    assert messages[0]["role"] == "system"
    assert MARKER not in messages[0]["content"]
    assert "Recent history:" not in messages[0]["content"]
    joined = [m["content"] for m in messages[1:]]
    assert sum(MARKER in c for c in joined) == 1
    assert messages[-1] == {"role": "user", "content": "next question"}
