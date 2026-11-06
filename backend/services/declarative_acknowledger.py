from __future__ import annotations

import re
from typing import Optional

from services.cognition_engine import (
    extract_explicit_backend_port,
    extract_explicit_goals,
    extract_explicit_projects,
)

USER_REPORTED_CHECK_PATTERN = re.compile(
    r"\bhealth\s*check\b[^.!?]*\bbackend\b[^.!?]*\bport\s+(?P<port>\d{2,5})\b[^.!?]*\b(?P<result>succeeded|successful|passed|failed|failure|unsuccessful)\b",
    re.IGNORECASE,
)


EXPLICIT_GOAL_PATTERN = re.compile(r"\bmy goal is to\b", re.IGNORECASE)
MAX_PROJECT_ACK_WORDS = 10


def _capitalize_first(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]


def _goal_ack_label(goal: str) -> str:
    cleaned = str(goal or "").strip(" .,!?:;")
    lowered = cleaned.lower()
    if lowered.startswith("add "):
        cleaned = cleaned[4:].strip()
    return _capitalize_first(cleaned)


def build_declarative_acknowledgement(message: str) -> Optional[str]:
    text = str(message or "").strip()
    if not text or "?" in text:
        return None

    report_match = USER_REPORTED_CHECK_PATTERN.search(text)
    if report_match:
        port = report_match.group("port")
        result = str(report_match.group("result") or "").lower()
        if result in {"succeeded", "successful", "passed"}:
            return (
                f"Understood. You reported that a health check for port {port} succeeded, "
                "but I have not independently verified that result."
            )
        return (
            f"Understood. You reported that a health check for port {port} failed, "
            "but I have not independently verified that result."
        )

    # The canned acknowledgement bypasses the model entirely, so it fires only on unmistakable
    # declarations. 2026-11-06: the broad goal patterns ("let's", "i want to", "we need to",
    # "i plan to") turned ordinary conversation into "X is now tracked as an active goal" — e.g.
    # "absolutely! let's refine them" — and the model then parroted that line on the next turn.
    # Goal *tracking* still uses the broad patterns; only this model-bypassing reply is narrowed.
    projects = extract_explicit_projects(text) if len(text.split()) <= MAX_PROJECT_ACK_WORDS else []
    goals = [g for g in extract_explicit_goals(text) if EXPLICIT_GOAL_PATTERN.search(text)]
    backend_port = extract_explicit_backend_port(text)

    if not projects and not goals and backend_port is None:
        return None

    lines = []
    if projects:
        lines.append(f"{projects[0]} is now recognized as an active project.")
    if goals:
        lines.append(f"{_goal_ack_label(goals[0])} is now tracked as an active goal.")
    if backend_port is not None:
        lines.append(f"The backend is configured to use port {backend_port}.")

    return "\n".join(lines) if lines else None
