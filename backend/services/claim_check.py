"""Tool-claim check (2026-11-06): a reply may not report a tool outcome that never happened.

Bill's voice chat: "It seems there was an issue integrating the new voice. The draft tool
couldn't find a working API." No tool ran that turn; the seat invented the failure. The number
check guards figures; this guards claims about the hands. Deterministic: a sentence that names a
registered command (underscores or spaces: "draft_tool" / "draft tool") together with an OUTCOME
word, when that command did not run this turn, gets a runtime note naming what actually ran.

Offers and explanations are not claims: "we can use draft_tool to ..." carries no outcome word.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Set, Tuple

_OUTCOME = re.compile(
    r"\b(?:failed|fails|couldn'?t|could not|was unable|wasn'?t able|didn'?t (?:find|work|return)|"
    r"did not (?:find|work|return)|returned|reported|found no|has been (?:filed|drafted|authored|"
    r"integrated|added|run|executed|completed|changed|switched|set)|have been (?:filed|drafted|"
    r"added)|ran|executed|completed|succeeded|there was an issue|an error|an issue (?:with|"
    r"integrating|running))\b", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def _spoken(name: str) -> str:
    return name.replace("_", " ").lower()


def claimed_but_not_run(reply: str, registered: Iterable[str],
                        ran: Sequence[str]) -> List[Tuple[str, str]]:
    """(command, sentence) for every outcome claim about a registered command that did not run
    this turn. Names are matched as whole phrases, underscored or spoken."""
    ran_set: Set[str] = {_spoken(r) for r in ran}
    text = str(reply or "")
    hits: List[Tuple[str, str]] = []
    for sentence in _SENTENCE.split(text):
        lowered = _spoken(sentence)
        if not _OUTCOME.search(lowered):
            continue
        for name in registered:
            spoken = _spoken(name)
            if spoken in ran_set:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(spoken)}(?![a-z0-9])", lowered):
                hits.append((name, sentence.strip()))
    # one entry per command, first sentence wins
    seen: Set[str] = set()
    unique = []
    for name, sentence in hits:
        if name not in seen:
            seen.add(name)
            unique.append((name, sentence))
    return unique


# ---------------------------------------------------------------- study and learning claims (2026-11-07)
# The joke conversation: "I've studied the Director Mel Brooks" after ONE web search returned five
# titles; "I've analyzed examples of jokes" after two; "I will learn from that" after nothing.
# Nothing is read in depth by a search, and nothing learns inside a conversation: the seat's
# weights do not change, and it keeps only this conversation's history. Deterministic: a study
# claim with no reading tool run this turn, or any promise to learn, gets a runtime note.
_STUDY_CLAIM = re.compile(
    r"\bI(?:'ve| have)\s+(?:now\s+|just\s+|thoroughly\s+|carefully\s+|already\s+)?"
    r"(?:studied|analy[sz]ed|researched|reviewed|read up on|read through|examined|absorbed|"
    r"gone through|looked into|looked at|familiari[sz]ed myself with)\b", re.IGNORECASE)
_LEARNING_PROMISE = re.compile(
    r"\bI(?:'ll| will|'m going to| am going to)\s+(?:definitely\s+|certainly\s+)?(?:learn|remember|"
    r"improve|do better|get better|not (?:do|repeat|make) (?:that|this|it|the same)|"
    r"(?:make sure|ensure|try|strive|aim)\s+(?:to\s+|that\s+I\s+)?(?:avoid|not|never|remember|improve|learn))\b|"
    r"\blesson learned\b|\bI(?:'ll| will) (?:keep|bear) (?:that|this) in mind\b",
    re.IGNORECASE)
# ("I've learned" is deliberately not matched: measured over 1,944 stored replies the only hit
# was "I am a synthesis of everything I've learned", a self-description, not a promise.)
READING_TOOLS = ("web_fetch", "browser_read", "own_browser_read", "deep_think")


def learning_note(reply: str, ran: Sequence[str]) -> str:
    """A note when the reply claims study the turn did not do, or promises learning the seat
    cannot do. Empty when neither applies, or when a reading tool really ran this turn."""
    text = str(reply or "")
    ran_list = list(dict.fromkeys(ran))
    lines: List[str] = []
    if _STUDY_CLAIM.search(text) and not any(r in READING_TOOLS for r in ran_list):
        searches = sum(1 for r in ran if r == "web_search")
        if searches:
            did = f"web_search ran {searches} time{'s' if searches != 1 else ''} and returned titles and snippets only"
        elif ran_list:
            did = f"only {', '.join(ran_list)} ran"
        else:
            did = "no tool ran"
        lines.append(f"the reply says it studied or analysed something, but this turn {did}; "
                     "nothing was read in depth")
    if _LEARNING_PROMISE.search(text):
        lines.append("the seat cannot learn or change within a conversation: its weights do not "
                     "change and it keeps only this conversation's history; lasting change comes "
                     "from the operator's consolidation training and from promoted proposals")
    if not lines:
        return ""
    return "---\n⚠ Learning check (runtime, not the seat): " + "; ".join(lines) + "."


def note_for(hits: List[Tuple[str, str]], ran: Sequence[str]) -> str:
    if not hits:
        return ""
    names = ", ".join(name for name, _ in hits)
    actually = ", ".join(dict.fromkeys(ran)) if ran else "no tool"
    return ("---\n⚠ Tool-claim check (runtime, not the seat): the reply reports an outcome for "
            f"{names}, but that tool did not run this turn ({actually} ran). Treat that claim as "
            "unverified; ask again and it should actually call the tool.")
