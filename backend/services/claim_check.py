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


def note_for(hits: List[Tuple[str, str]], ran: Sequence[str]) -> str:
    if not hits:
        return ""
    names = ", ".join(name for name, _ in hits)
    actually = ", ".join(dict.fromkeys(ran)) if ran else "no tool"
    return ("---\n⚠ Tool-claim check (runtime, not the seat): the reply reports an outcome for "
            f"{names}, but that tool did not run this turn ({actually} ran). Treat that claim as "
            "unverified; ask again and it should actually call the tool.")
