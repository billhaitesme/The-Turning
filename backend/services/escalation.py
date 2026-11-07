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


# ---------------------------------------------------------------- craft requests (2026-11-07)
# Live, the joke conversation: twenty minutes, four repeat-guard stops, two web searches dressed
# up as "I've studied Mel Brooks", and not one joke. Humour and verse are the things an 8B does
# worst, and it cannot tell that it is failing. The runtime sends a clearly creative request to
# the frontier rung framed as WRITE (not analyse: the 30B, asked by the seat, returned a lecture
# on setup/punchline structure) and the seat delivers the piece. Identity stays local; the craft
# is borrowed (ADR 0026). Frontier only: the frontier applies its own judgement to what it will
# write, and the runtime never hands a creative request to the local deep rung. Breaker OFF: no
# hand-off; the seat answers as before.
_CRAFT_VERB = (r"\b(?:tell|write|give|make up|come up with|compose|create|do|try|craft|invent|pen|"
               r"draft|recite|improvise|perform|hit me with|lay|say)\b")
_CRAFT_NOUN = (r"\b(?:jokes?|puns?|limericks?|poems?|poetry|haikus?|sonnets?|songs?|lyrics|verses?|"
               r"raps?|toasts?|roasts?|eulogy|speech|(?:short |bedtime |tall )?stor(?:y|ies)|tale|"
               r"riddles?|one-?liners?|(?:comedy |comic |stand-?up )?(?:bit|routine|set|monologue)|"
               r"insults?|comebacks?|slogans?|taglines?|parody|satire|fable|epigram)\b")
_CRAFT = re.compile(_CRAFT_VERB + r"[^.?!]{0,40}?" + _CRAFT_NOUN, re.IGNORECASE)
_CRAFT_STYLE = re.compile(r"\bin the (?:style|voice|manner|spirit) of\b", re.IGNORECASE)
_CRAFT_NOUN_ALONE = re.compile(_CRAFT_NOUN, re.IGNORECASE)
# "another one", "funnier", "try again": a retry stays a craft request only while the previous
# reply was the runtime's own craft hand-off (the detector sees one message, not the thread)
_CRAFT_RETRY = re.compile(
    r"\b(?:another|different|better|funnier|again|one more|next one|go ahead|you may try|try it|"
    r"do it|hit me|more)\b", re.IGNORECASE)
_NOT_CRAFT = re.compile(
    r"\b(?:explain|why (?:is|was|isn'?t|wasn'?t) (?:that|this|it)|what (?:is|was|makes)|how (?:is|was|does)|"
    r"analy[sz]e|meaning|definition|history of|who (?:is|was|wrote))\b", re.IGNORECASE)


def craft_reason(message: str, previous_reply: str = "") -> Optional[str]:
    """Why this message is a request for a creative piece, or None. A follow-up such as
    "another one" counts only when the previous reply was itself a craft hand-off."""
    text = str(message or "").strip()
    if not text or len(text) > MAX_CHARS or text.lower().startswith(BODY_BRIEF_PREFIX):
        return None
    if _NOT_CRAFT.search(text) and not _CRAFT.search(text):
        return None  # "explain why that's funny" is a question, not a commission
    if _CRAFT.search(text) or (_CRAFT_STYLE.search(text) and _CRAFT_NOUN_ALONE.search(text)):
        return "creative piece requested"
    if CRAFT_ANNOUNCE in str(previous_reply or "") and len(text) <= 80 and _CRAFT_RETRY.search(text):
        return "retry of a creative piece"
    return None


# ---------------------------------------------------------------- craft routing (2026-11-07)
# Bill: "Claude is better at the telling" (jokes). CLEAN creative goes to the operator's Claude
# Code CLI — Claude sees the real request and applies its own judgment. Anything explicit, adult,
# or personal is written by the LOCAL gear and never leaves the machine. The triage is
# CONSERVATIVE by construction: the operator's override, an explicit-lexicon hit, the breaker
# being OFF, a classifier answer that is not a clear YES, or any classifier failure — all stay
# local. Doubt stays home.
_KEEP_LOCAL = re.compile(
    r"\b(?:keep (?:this|it) local|local(?:ly)? only|privately|in private|incognito|"
    r"just between us|don'?t send (?:this|it)|off(?:-| )machine|no cloud)\b", re.IGNORECASE)
_EXPLICIT = re.compile(
    r"\b(?:explicit|nsfw|erotic|erotica|sexual|sexy|sext\w*|nude|naked|porn\w*|smut\w*|kink\w*|"
    r"fetish|x-?rated|adults? only|dirty (?:joke|story|limerick|poem)|filthy|raunchy|lewd|"
    r"obscene|hardcore)\b", re.IGNORECASE)

CLEAN_QUESTION = (
    "Answer with exactly one word, YES or NO. May this writing request be sent to a public "
    "cloud writing assistant? Answer NO if it involves or implies explicit or sexual content, "
    "adult themes, real private people, or the operator's personal information. Otherwise YES."
    "\n\nREQUEST: {request}")


def craft_rung(message: str, *, breaker_on: bool, classify) -> str:
    """'claude' for clean creative via the operator's CLI, 'local' for everything else."""
    text = str(message or "")
    if not breaker_on or _KEEP_LOCAL.search(text) or _EXPLICIT.search(text):
        return "local"
    try:
        verdict = str(classify(CLEAN_QUESTION.format(request=text)) or "").strip().upper()
    except Exception:  # noqa: BLE001 — a failed triage stays home
        return "local"
    return "claude" if verdict.startswith("YES") else "local"


CRAFT_ANNOUNCE = "Let me work on that one properly — a moment."
CRAFT_TASK = (
    "WRITE the piece the operator asked for: the finished text itself and nothing else. No "
    "analysis, no explanation of why it works, no preamble, no list of options unless asked, no "
    "headings. Keep any style, voice or subject the operator named. If it is a joke, one joke, "
    "tight, with an actual punchline.\n\nOPERATOR'S REQUEST: {request}"
)
CRAFT_NOTE = (
    "The runtime had a stronger rung write the piece the operator asked for ({reason}): the tool "
    "result above holds the finished text in its 'answer'. Deliver that text to the operator as "
    "written: verbatim, no analysis, no explanation of why it works, no extra attempt of your "
    "own. If the rung declined or returned nothing usable, say so in one plain sentence."
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
    r"(?:what|which) (?:time ?zone|timezone|model|version|build|machine|computer|pc) are you|"
    r"your (?:time ?zone|timezone|utc offset|clock|location|host|machine|model|version)|"
    r"where are you(?: located| running| based)?\b|"
    r"can you (?:hear|see|speak|talk|code|remember|access)|"
    r"(?:do|can|will|could) you (?:learn|improve|get smarter|grow|evolve)|learn from (?:this|that|it|your mistakes?)|"
    r"(?:will|do) you remember (?:this|that|it)|"
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
