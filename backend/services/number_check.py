"""Number grounding for tool-using replies (2026-11-06).

Found live: the seat (8B) called exchange_rate, the tool returned NOK 9.4277, and the seat told
the operator 9.2984. Asked to quote the raw output, it invented a different payload dated 2023.
Prompt rules do not stop a small model from paraphrasing numbers, so the runtime checks them.

Deterministic and model-free: every decimal number in the final reply must appear in what the
tools returned this turn (or in the operator's own message), allowing the reply to round or
truncate. Anything else is flagged to the operator with the tools' actual values beside it.
When no tool ran this turn, decimals in the reply are marked as from memory, not a live lookup.
The reply has already streamed, so this appends a visible note; it never edits the seat's words.

Scope is deliberately narrow: decimals only (rates, temperatures, readings). Integers are dates,
counts and list numbers far too often to judge without false alarms.
"""
from __future__ import annotations

import json
import re
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# A decimal number not glued to other digits/dots: excludes versions (0.5.2) and IPs.
_REPLY_DECIMAL = re.compile(r"(?<![\d.,])((?:\d{1,3}(?:,\d{3})+|\d+)\.\d+)(?!\.?\d)")
# Any number in source text (tool JSON, operator message).
_SOURCE_NUMBER = re.compile(r"\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")

MAX_TOOLS_SHOWN = 3
MAX_OUTPUT_CHARS = 300


def _to_decimal(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def reply_decimals(reply: str) -> List[str]:
    """Decimal numbers as written in the reply, in order, de-duplicated."""
    seen: List[str] = []
    for match in _REPLY_DECIMAL.finditer(reply or ""):
        token = match.group(1)
        if token not in seen:
            seen.append(token)
    return seen


def source_numbers(texts: Iterable[str]) -> List[Decimal]:
    numbers: List[Decimal] = []
    for text in texts:
        for token in _SOURCE_NUMBER.findall(text or ""):
            value = _to_decimal(token)
            if value is not None:
                numbers.append(value)
    return numbers


def is_grounded(token: str, sources: Sequence[Decimal]) -> bool:
    """True when the reply's number equals a source number, or is that number rounded or
    truncated to the reply's own precision (9.43 / 9.42 / 9.4 all ground on 9.4277)."""
    value = _to_decimal(token)
    if value is None:
        return True  # nothing to judge
    places = Decimal(1).scaleb(value.as_tuple().exponent)  # e.g. Decimal("0.01")
    for source in sources:
        if source == value:
            return True
        try:
            if (source.quantize(places, rounding=ROUND_HALF_UP) == value
                    or source.quantize(places, rounding=ROUND_DOWN) == value):
                return True
        except InvalidOperation:
            continue
    return False


def _shown_output(result: Dict[str, Any]) -> str:
    outcome = result.get("outcome")
    if isinstance(outcome, dict) and isinstance(outcome.get("output"), str):
        text = outcome["output"]
    else:
        text = json.dumps(outcome if outcome is not None else result, ensure_ascii=False)
    return text if len(text) <= MAX_OUTPUT_CHARS else text[:MAX_OUTPUT_CHARS] + " …"


def check_reply(reply: str, tool_results: Sequence[Tuple[str, Dict[str, Any]]],
                operator_message: str = "") -> Tuple[List[str], str]:
    """Return (unverified_numbers, note). The note is empty when nothing needs flagging.

    tool_results: (tool_name, result) for every tool call the runtime answered this turn. Only
    executed results count as evidence; with none, there is nothing to check against."""
    executed = [(name, result) for name, result in tool_results
                if isinstance(result, dict) and result.get("status") == "executed"]
    if not executed:
        # Found live the same morning: asked "use your tools now ... forecast for Bergen", the
        # seat called nothing and re-served the earlier Oslo numbers from chat history as Bergen.
        # With no lookup this turn, decimals cannot be checked; say so instead of staying silent.
        from_memory = [t for t in reply_decimals(reply)
                       if not is_grounded(t, source_numbers([operator_message]))]
        if not from_memory:
            return [], ""
        return from_memory, ("---\n⚠ Number check (runtime, not the seat): no tool ran this turn, "
                             "so " + ", ".join(from_memory) + " came from memory or the "
                             "conversation, not a live lookup. Ask again to have them fetched.")
    sources = source_numbers([json.dumps(r, ensure_ascii=False) for _, r in executed]
                             + [operator_message])
    unverified = [t for t in reply_decimals(reply) if not is_grounded(t, sources)]
    if not unverified:
        return [], ""
    lines = [
        "---",
        "⚠ Number check (runtime, not the seat): "
        + ", ".join(unverified)
        + (" does" if len(unverified) == 1 else " do")
        + " not match anything the tools returned this turn. Treat as unverified. "
          "What the tools actually returned:",
    ]
    for name, result in executed[:MAX_TOOLS_SHOWN]:
        lines.append(f"- {name}: {_shown_output(result)}")
    return unverified, "\n".join(lines)
