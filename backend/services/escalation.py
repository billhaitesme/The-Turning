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


# ---------------------------------------------------------------- the say-do gap (2026-11-06)
# Live: "Let me examine my current capabilities ... I'll start by checking my available tools."
# and the reply ended. No tool ran. A reply whose closing words promise an action, from a turn
# that called nothing in that round, gets sent back once to do it.
_PROMISE = re.compile(
    r"\b(?:let me|i'?ll|i will|i'?m going to|i am going to)\s+(?:now\s+|first\s+|quickly\s+)?"
    r"(?:start by\s+|begin by\s+)?(?:check|checking|examine|examining|look|looking|search|"
    r"searching|find|finding|run|running|fetch|fetching|query|verify|review|reviewing|inspect|"
    r"inspecting|scan|scanning|go through|pull up|test|testing|investigate|call|calling|"
    r"try|retry|search again|try again)\b",
    re.IGNORECASE)
PROMISE_TAIL_CHARS = 260

PROMISE_NUDGE = (
    "You just said you would do something, but you called no tool, so nothing happened. Do it "
    "now: call the tool that does it and report the result. If no tool can do it, say so "
    "plainly in one sentence. Do not repeat what you already said."
)


# ---------------------------------------------------------------- self-questions (2026-11-06)
# Live: asked "what can you do today ... examine yourself", the seat first wrote "I can write and
# execute code ... make changes to my configuration" (false) and only THEN called describe_self.
# For questions about OMEGA itself, the runtime reads describe_self FIRST (a fast local read,
# no model call) so the seat answers from the facts instead of its priors.
_SELF_QUESTION = re.compile(
    r"\b(?:examine yourself|about yourself|describe yourself|tell me about you|who are you|"
    r"what (?:can|can't|cannot) you(?: actually)? do|what are you capable of|"
    r"your (?:voice|voices|capabilities|abilities|limits|limitations|body|settings|tools|setup|senses)|"
    r"(?:other|more|new|different|additional) voices?|download(?:ed|ing)? (?:a |more |new |other )?voices?|"
    r"can you (?:hear|see|speak|talk|code|remember|access)|"
    r"can you (?:write|change|edit|modify) (?:code|yourself|your own)|are you able to|"
    r"what(?:'s| is) missing)\b", re.IGNORECASE)
SELF_NOTE = (
    "The runtime read describe_self because the operator asked about you. The tool result "
    "above is the truth about your body, settings and limits. Answer from it. Claim no ability "
    "it does not list; if it says you cannot do something, say so plainly."
)


def self_question(message: str) -> bool:
    text = str(message or "").strip()
    return len(text) <= MAX_CHARS and not text.lower().startswith(BODY_BRIEF_PREFIX) \
        and bool(_SELF_QUESTION.search(text))


_CONDITIONAL = re.compile(r"\b(?:when you|once you|if you|after you|whenever you)\b", re.IGNORECASE)


def promises_action(round_text: str) -> bool:
    """True when the closing words of a round promise an action ("let me check ..."). A promise
    that waits on the operator ("when you're ready ... I'll run it") is not an empty one.
    Scanned over OMEGA's 886 replies to Bill: fires on 2, both real empty promises."""
    # Only the CLOSING sentence: a promise followed by the actual content ("Let me try again with
    # a better one: <joke>") is not empty. Every real empty promise found ended the reply.
    tail = str(round_text or "")[-PROMISE_TAIL_CHARS:].strip()
    sentences = [s for s in re.split(r"(?<=[.!?:])\s+", tail) if s.strip()]
    if not sentences:
        return False
    last = sentences[-1]
    return bool(_PROMISE.search(last)) and not _CONDITIONAL.search(last)
