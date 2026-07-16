from __future__ import annotations

import re
from typing import Any, Dict, List

RUNTIME_DECLARATION_PATTERN = re.compile(
    r"\b(?:the\s+)?(?P<subject>[a-z0-9][a-z0-9_\- ]{0,60})\s+"
    r"(?:is|was|seems)\s+"
    r"(?P<status>online|offline|connected|ready|readable|installed|available|loaded|healthy|configured|verified)\b",
    re.IGNORECASE,
)


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return lowered or "resource"


def _runtime_key(subject_slug: str, status: str) -> str:
    if subject_slug in {"backend", "api", "server", "backend_server"} and status in {"online", "offline"}:
        return "backend_health"

    if status in {"online", "offline"}:
        return f"{subject_slug}_health"
    if status == "connected":
        return f"{subject_slug}_connected"
    if status == "ready":
        return f"{subject_slug}_ready"
    if status == "readable":
        return f"{subject_slug}_readable"
    if status == "installed":
        return f"{subject_slug}_installed"
    if status == "available":
        return f"{subject_slug}_available"
    if status == "loaded":
        return f"{subject_slug}_loaded"
    if status == "healthy":
        return f"{subject_slug}_healthy"
    if status == "configured":
        return f"{subject_slug}_configured"
    if status == "verified":
        return f"{subject_slug}_verified"

    return f"{subject_slug}_state"


BOOLEAN_STATUSES = {
    "installed",
    "available",
    "loaded",
    "healthy",
    "configured",
    "verified",
}

HEALTH_CHECK_REPORT_PATTERN = re.compile(
    r"\bhealth\s*check\b[^.!?]*\bbackend\b[^.!?]*(?:\bport\s+(?P<port>\d{2,5})\b)?[^.!?]*\b(?P<result>succeeded|successful|passed|failed|failure|unsuccessful)\b",
    re.IGNORECASE,
)


def extract_runtime_declarations(message: str) -> List[Dict[str, Any]]:
    declarations: List[Dict[str, Any]] = []

    report_match = HEALTH_CHECK_REPORT_PATTERN.search(message or "")
    if report_match:
        result = str(report_match.group("result") or "").lower()
        success = result in {"succeeded", "successful", "passed"}
        declarations.append(
            {
                "key": "backend_health",
                "value": "online" if success else "offline",
                "state_type": "declared",
                "source": "user",
                "confidence": 1.0,
                "dependencies": ["backend_port"],
                "scope": "runtime",
                "notes": "User reports successful health check." if success else "User reports failed health check.",
                "observed_at": None,
                "expires_at": None,
                "checked_at": None,
                "checked_url": None,
            }
        )

    for match in RUNTIME_DECLARATION_PATTERN.finditer(message or ""):
        subject_slug = _slug(match.group("subject"))
        status = match.group("status").lower()
        key = _runtime_key(subject_slug, status)
        value: Any = True if status in BOOLEAN_STATUSES else status

        declarations.append(
            {
                "key": key,
                "value": value,
                "state_type": "declared",
                "source": "user",
                "confidence": 1.0,
                "dependencies": [],
                "scope": "runtime",
                "notes": "User reported runtime status; not independently verified.",
                "observed_at": None,
                "expires_at": None,
            }
        )

    # Preserve first occurrence of each key in a message to avoid duplicate inserts.
    deduped: Dict[str, Dict[str, Any]] = {}
    for record in declarations:
        if record["key"] not in deduped:
            deduped[record["key"]] = record

    return list(deduped.values())
