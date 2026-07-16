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

    projects = extract_explicit_projects(text)
    goals = extract_explicit_goals(text)
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
