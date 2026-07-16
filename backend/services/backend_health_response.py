from __future__ import annotations

import re
from typing import Any, Dict

from services.evidence_engine import normalize_evidence_record


BACKEND_HEALTH_QUERY_PATTERN = re.compile(r"\bis\s+the\s+backend\s+online(?:\s+now)?\s*\??$", re.IGNORECASE)
HEALTH_CHECK_REQUEST_PATTERN = re.compile(
    r"\b(?:can|could|please|will)\b[^.!?]*\b(?:you)\b[^.!?]*\b(?:perform|preform|run)\b[^.!?]*\bhealth\s*check\b",
    re.IGNORECASE,
)


def is_backend_health_query(message: str) -> bool:
    return bool(BACKEND_HEALTH_QUERY_PATTERN.search(str(message or "").strip()))


def is_health_check_execution_request(message: str) -> bool:
    return bool(HEALTH_CHECK_REQUEST_PATTERN.search(str(message or "").strip()))


def build_health_check_execution_response(evidence_store: Dict[str, Any]) -> str:
    facts = evidence_store.get("facts", {}) if isinstance(evidence_store, dict) else {}
    if not isinstance(facts, dict):
        facts = {}

    backend_port = normalize_evidence_record(facts.get("backend_port")).get("value")
    if backend_port is None:
        return (
            "I cannot run a trusted health-check adapter from this chat. "
            "If you run one externally and provide the structured result, I can apply verified runtime evidence."
        )

    return (
        f"I cannot run a trusted health-check adapter from this chat. "
        f"Run a trusted check against http://127.0.0.1:{backend_port} and submit the structured result to record verified runtime evidence."
    )


def build_backend_health_response(evidence_store: Dict[str, Any]) -> str:
    facts = evidence_store.get("facts", {}) if isinstance(evidence_store, dict) else {}
    if not isinstance(facts, dict):
        facts = {}

    backend_port = normalize_evidence_record(facts.get("backend_port")).get("value")
    backend_health = normalize_evidence_record(facts.get("backend_health"))

    state_type = backend_health.get("state_type")
    value = backend_health.get("value")
    source = str(backend_health.get("source") or "")
    checked_at = backend_health.get("checked_at") or backend_health.get("observed_at")
    checked_url = backend_health.get("checked_url")

    configured_endpoint = f"http://127.0.0.1:{backend_port}" if backend_port is not None else None
    endpoint_matches = bool(configured_endpoint and checked_url and str(checked_url).strip() == configured_endpoint)

    if state_type in {"verified", "observed"} and source == "health_check" and value in {"online", "offline"}:
        if value == "online" and endpoint_matches:
            return "The backend is verified online at the currently configured endpoint."

        if value == "online":
            return (
                "A trusted health check reported the backend online, but the checked endpoint does not match "
                "the currently configured backend endpoint."
            )

        if endpoint_matches:
            return "The backend is verified offline at the currently configured endpoint."

        return (
            "A trusted health check reported the backend offline, but the checked endpoint does not match "
            "the currently configured backend endpoint."
        )

    if state_type == "declared" and source == "user" and value in {"online", "offline"}:
        return (
            f"The backend is reported as {value} by user declaration, "
            "but I have not independently verified that result."
        )

    if backend_port is not None:
        return (
            f"The backend is configured to use port {backend_port}, "
            "but runtime health has not been independently verified."
        )

    return "Backend runtime health has not been independently verified."
