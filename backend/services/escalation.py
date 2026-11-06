"""When the runtime sends a message up the Mind Ladder itself (2026-11-06).

Found live: asked the Tuesday-boy probability puzzle, the 8B seat never called deep_think. It
answered inline and contradicted itself (25/27 in the working, 13/27 boxed). The same model,
given think=True through deep_think, solved it and two other hard questions 3/3. The seat is a
poor judge of when it needs depth; prompt rules have not fixed that. So a deterministic detector
spots messages that are clearly multi-step problems and the runtime runs deep_think first.

Deliberately narrow (a false positive costs the operator one to three minutes):
  - puzzle / probability language ("probability", "odds", "riddle", "logic puzzle", ...)
  - a quantitative word problem: a question with at least two numbers AND a quantity cue
    ("how long", "what time", "arrive", "how many", "total", "rate", ...)
  - an explicit request for a plan / schedule / itinerary / strategy
It never fires on jokes, short messages, or when the operator asks for a quick answer.
"""
from __future__ import annotations

import re
from typing import Optional

MIN_CHARS = 40
# Measured over Bill's 978 real messages: median 29 chars, p99 242, none of his own over 1000.
# Longer text is pasted material or a body brief, not a question to escalate.
MAX_CHARS = 1000
# The Ø2-02 bridge opens every body brief with this header (75 in the store, 700-2300 chars);
# a brief mentioning speeds and times must never stall the dog for minutes of deep thought.
BODY_BRIEF_PREFIX = "operating context"

_PUZZLE = re.compile(
    r"\b(probability|probabilities|odds of|odds that|chance that|chances that|expected value|"
    r"riddle|logic (?:puzzle|problem)|brain ?teaser|puzzle|prove that)\b", re.IGNORECASE)
_QUANTITY_CUE = re.compile(
    r"\b(how (?:long|many|much|far|fast|often)|what time|when will|arrive|arrival|eta|total|"
    r"average|rate|percent|per (?:hour|day|week|month|year)|knots|mph|km/?h|speed|cost|"
    r"interest|budget|split|divide|convert)\b", re.IGNORECASE)
_SOLVE_VERB = re.compile(r"\b(calculate|compute|work out|figure out|solve)\b", re.IGNORECASE)
_PLAN = re.compile(
    r"\b(make|draft|write|build|give me|put together|create|plan out)\b[^.?!]{0,40}?"
    r"\b(plan|schedule|itinerary|roadmap|strategy|timeline)\b", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:[.,:]\d+)?")
_NEVER = re.compile(
    r"\b(joke|jokes|funny|pun|quick(?:ly)?|short answer|briefly|in a word|don'?t think|"
    r"off the top of your head|ballpark)\b", re.IGNORECASE)


def deep_task_reason(message: str) -> Optional[str]:
    """Why this message should go up the ladder, or None. Pure function of the operator's text."""
    text = str(message or "").strip()
    if not MIN_CHARS <= len(text) <= MAX_CHARS or _NEVER.search(text):
        return None
    if text.lower().startswith(BODY_BRIEF_PREFIX):
        return None
    if _PUZZLE.search(text):
        return "puzzle or probability question"
    numbers = len(_NUMBER.findall(text))
    asks = "?" in text or bool(_SOLVE_VERB.search(text))
    if asks and numbers >= 2 and _QUANTITY_CUE.search(text):
        return "multi-step calculation"
    if _PLAN.search(text):
        return "request for a plan"
    return None


ANNOUNCE = "Working this one through properly — give me a minute or two."
SEAT_NOTE = (
    "The runtime sent the operator's message to deep_think first because it is a multi-step "
    "problem ({reason}). Its reasoning is in the tool result above. Check it, then give the "
    "operator a clear, correct final answer in your own words. If the deep reasoning and your "
    "own check disagree, say which you trust and why."
)
