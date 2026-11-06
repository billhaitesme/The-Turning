"""Repeat guard for the agent loop (2026-11-06).

Found in Bill's chat (5f35d436): the 8B seat sent the SAME ~470-character reply six times in a
row, to "that was terrible", "think deeper", "go learn a better joke" and "tell me a different
joke" alike. The prompt already said "never repeat your previous reply"; a small model copying
from its own context ignores that. So the runtime watches the stream instead.

How it works (deterministic, model-free):
- The loop holds back the newest HOLD_CHARS of visible text while it streams. Each new chunk,
  the guard takes the reply's latest WINDOW_WORDS words and asks what share of their word
  triples already appear in an earlier assistant reply of this conversation (or earlier in
  this same reply). At COPY_SHARE or more, the seat is copying: the stream is stopped before
  the copied text is shown.
- Triples, not exact text, because the live failure also came as a word-swap ("black man ...
  party ... drinks" -> "woman ... bar ..."), and as the same joke twice inside one reply.
  Measured on the real conversations: every repeat scored 0.89-1.00; every normal reply,
  including four different jokes in a row and two forecasts for different cities, scored
  0.50 or less. Numbers are their own words, so templated readings with new values differ.
- The loop retries once with the copied replies withheld from the context (nothing left to
  copy) and a short instruction to answer the latest message afresh.
- If the retry copies too, the loop stops and says so plainly instead of sending the repeat.

The guard stands down when the operator asks for a repeat ("repeat that", "say it again",
"word for word", ...). Text shorter than the window is never judged: short stock phrases
("Done.", "Approved.") repeat legitimately.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Set, Tuple

WINDOW_WORDS = 30   # the newest words judged each time
COPY_SHARE = 0.75   # share of the window's word triples already said = copying
HOLD_CHARS = 240    # raw characters held back from the stream (~40 words) so a copy is caught
                    # before any of it is shown

WITHHELD = "[earlier reply withheld by the runtime: you kept repeating it word for word]"
RETRY_INSTRUCTION = (
    "Your draft was repeating one of your earlier replies word for word, so the runtime stopped "
    "it. Answer the operator's LATEST message afresh. Do not reuse earlier wording; if you cannot "
    "do what was asked, say so plainly in one sentence."
)
GAVE_UP_NOTE = (
    "---\n⚠ Repeat guard (runtime, not the seat): the seat tried to send an earlier reply again, "
    "twice, so it was stopped. Rephrase the request, or ask for something different."
)

_EXEMPT = re.compile(
    r"\b(repeat|word for word|verbatim|one more time|say (?:that|it) again|"
    r"same (?:answer|reply|thing) again|copy (?:that|it))\b", re.IGNORECASE)
_WORD = re.compile(r"[a-z0-9]+(?:['.][a-z0-9]+)*")

Triple = Tuple[str, str, str]


def words(text: str) -> List[str]:
    """Lower-case words; markup, punctuation and spacing fall away. '3.2' stays one word."""
    return _WORD.findall(str(text or "").lower())


def triples(ws: Sequence[str]) -> List[Triple]:
    return [(ws[i], ws[i + 1], ws[i + 2]) for i in range(len(ws) - 2)]


def share(window: Sequence[Triple], said: Set[Triple]) -> float:
    return sum(t in said for t in window) / len(window) if window else 0.0


class RepeatGuard:
    def __init__(self, previous_replies: Sequence[str], operator_message: str = "") -> None:
        self.exempt = bool(_EXEMPT.search(operator_message or ""))
        self._sources = [(set(triples(words(r))), r) for r in previous_replies
                         if len(words(r)) >= WINDOW_WORDS]
        self.matched: List[str] = []  # the earlier replies the seat copied from
        self.fresh_numbers: Set[str] = set()

    def saw_tool_result(self, result_text: str) -> None:
        """Numbers a tool returned THIS turn are fresh evidence: "what's the forecast again?"
        answered from a new fetch legitimately repeats the earlier reply, so a stretch of text
        carrying those numbers is never judged a copy. A copied block with no fresh reading in
        it (the 15:14 joke after a host-status call) is still judged."""
        self.fresh_numbers.update(w for w in words(result_text) if any(ch.isdigit() for ch in w))

    def copying(self, round_text: str) -> bool:
        """True when the newest WINDOW_WORDS of this round's text are mostly already said:
        in an earlier reply, or earlier in this same text."""
        if self.exempt:
            return False
        ws = words(round_text)
        if len(ws) < WINDOW_WORDS:
            return False
        if any(w in self.fresh_numbers for w in ws[-WINDOW_WORDS:]):
            return False  # this stretch reports readings a tool fetched this turn: not a copy
        window = triples(ws[-WINDOW_WORDS:])
        hits = [original for said, original in self._sources if share(window, said) >= COPY_SHARE]
        for original in hits:
            if original not in self.matched:
                self.matched.append(original)
        earlier_here = set(triples(ws[:-WINDOW_WORDS]))
        return bool(hits) or share(window, earlier_here) >= COPY_SHARE

    def withhold(self, conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """The conversation for the retry: every copied-from reply replaced by a marker."""
        out = []
        for message in conversation:
            if message.get("role") == "assistant" and message.get("content") in self.matched:
                message = {**message, "content": WITHHELD}
            out.append(message)
        return out
