from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_EVIDENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "evidence.json"
)

STATE_RANK = {
    "unknown": 0,
    "declared": 1,
    "configured": 2,
    "inferred": 2,
    "observed": 3,
    "verified": 4,
    "invalidated": -1,
    "expired": -1,
}


def empty_evidence_record(
    *,
    key: Optional[str] = None,
    value: Any = None,
    state_type: str = "unknown",
    source: str = "system",
    confidence: float = 0.0,
    observed_at: Optional[str] = None,
    expires_at: Optional[str] = None,
    dependencies: Optional[list] = None,
    scope: Optional[str] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "key": key or "",
        "value": value,
        "state_type": str(state_type).lower() if str(state_type).lower() in STATE_RANK else "unknown",
        "source": source,
        "confidence": confidence,
        "observed_at": observed_at,
        "expires_at": expires_at,
        "dependencies": list(dependencies or []),
        "scope": scope,
        "notes": notes,
    }


def normalize_evidence_record(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return empty_evidence_record()

    normalized = deepcopy(record)
    normalized.setdefault("key", None)
    normalized.setdefault("value", None)
    normalized.setdefault("state_type", "unknown")
    normalized.setdefault("source", "system")
    normalized.setdefault("confidence", 0.0)
    normalized.setdefault("observed_at", None)
    normalized.setdefault("expires_at", None)
    normalized.setdefault("dependencies", [])
    normalized.setdefault("scope", None)
    normalized.setdefault("notes", "")

    if not isinstance(normalized.get("dependencies"), list):
        normalized["dependencies"] = []

    state_type = str(normalized.get("state_type", "unknown")).lower()
    normalized["state_type"] = state_type if state_type in STATE_RANK else "unknown"

    try:
        normalized["confidence"] = max(0.0, min(1.0, float(normalized.get("confidence", 0.0))))
    except (TypeError, ValueError):
        normalized["confidence"] = 0.0

    return normalized


def load_evidence_store(path: Path = DEFAULT_EVIDENCE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 1, "facts": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "facts": {}}

    if not isinstance(data, dict):
        return {"version": 1, "facts": {}}

    if not isinstance(data.get("facts"), dict):
        data["facts"] = {}

    data.setdefault("version", 1)
    data["facts"] = {key: normalize_evidence_record(value) for key, value in data["facts"].items()}

    return data


def save_evidence_store(store: Dict[str, Any], path: Path = DEFAULT_EVIDENCE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")


def rank_state_type(state_type: str) -> int:
    return STATE_RANK.get(str(state_type).lower(), 0)


def rank_state(state_type: str) -> int:
    return rank_state_type(state_type)


def should_replace_evidence(existing: Optional[Dict[str, Any]], proposed: Optional[Dict[str, Any]]) -> bool:
    existing_record = normalize_evidence_record(existing)
    proposed_record = normalize_evidence_record(proposed)

    if existing_record.get("state_type") == "unknown":
        return True

    if proposed_record.get("state_type") == "unknown":
        return False

    if rank_state_type(proposed_record.get("state_type")) > rank_state_type(existing_record.get("state_type")):
        return True

    if rank_state_type(proposed_record.get("state_type")) < rank_state_type(existing_record.get("state_type")):
        return False

    if proposed_record.get("confidence", 0.0) > existing_record.get("confidence", 0.0):
        return True

    if proposed_record.get("confidence", 0.0) < existing_record.get("confidence", 0.0):
        return False

    if proposed_record.get("source") != existing_record.get("source"):
        return True

    if proposed_record.get("value") != existing_record.get("value"):
        return True

    return False


def should_replace(existing: Optional[Dict[str, Any]], proposed: Optional[Dict[str, Any]]) -> bool:
    return should_replace_evidence(existing, proposed)


def get_evidence(store: Dict[str, Any], key: str) -> Dict[str, Any]:
    facts = store.get("facts", {}) if isinstance(store, dict) else {}
    if not isinstance(facts, dict):
        return empty_evidence_record(key=key)
    return normalize_evidence_record(facts.get(key))


def set_evidence(store: Dict[str, Any], *, key: str, record: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(store)
    updated.setdefault("version", 1)
    updated.setdefault("facts", {})

    proposed = normalize_evidence_record(record)
    proposed["key"] = key
    existing = normalize_evidence_record(updated["facts"].get(key))

    if should_replace_evidence(existing, proposed):
        updated["facts"][key] = proposed

    return updated


def promote_evidence(store: Dict[str, Any], *, key: str, record: Dict[str, Any]) -> Dict[str, Any]:
    return set_evidence(store, key=key, record=record)


def demote_evidence(store: Dict[str, Any], *, key: str, record: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(store)
    updated.setdefault("version", 1)
    updated.setdefault("facts", {})

    proposed = normalize_evidence_record(record)
    proposed["key"] = key

    if should_replace_evidence(normalize_evidence_record(updated["facts"].get(key)), proposed):
        updated["facts"][key] = proposed

    return updated


def remove_evidence(store: Dict[str, Any], key: str) -> Dict[str, Any]:
    updated = deepcopy(store)
    updated.setdefault("facts", {})
    updated["facts"].pop(key, None)
    return updated


def invalidate_evidence(store: Dict[str, Any], key: str, *, notes: str = "") -> Dict[str, Any]:
    updated = deepcopy(store)
    updated.setdefault("facts", {})

    existing = normalize_evidence_record(updated["facts"].get(key))
    if existing.get("state_type") == "unknown":
        return updated

    existing["state_type"] = "invalidated"
    existing["notes"] = notes or existing.get("notes") or "evidence invalidated"
    existing["observed_at"] = None
    existing["expires_at"] = None
    updated["facts"][key] = existing
    return updated


def invalidate_dependents(store: Dict[str, Any], dependency_key: str) -> Dict[str, Any]:
    updated = deepcopy(store)
    facts = updated.setdefault("facts", {})

    for key, record in list(facts.items()):
        if key == dependency_key:
            continue

        dependencies = record.get("dependencies") or []
        scope = record.get("scope")
        if dependency_key in dependencies or (isinstance(scope, str) and dependency_key in scope):
            record["state_type"] = "unknown"
            record["observed_at"] = None
            record["expires_at"] = None
            record["notes"] = f"dependency {dependency_key} changed"

    return updated


def invalidate_dependent_evidence(store: Dict[str, Any], *, dependency_key: str) -> Dict[str, Any]:
    return invalidate_dependents(store, dependency_key)


def is_evidence_fresh(record: Optional[Dict[str, Any]], *, now: Optional[datetime] = None) -> bool:
    normalized = normalize_evidence_record(record)
    if normalized.get("state_type") in {"unknown", None}:
        return False
    if normalized.get("state_type") in {"expired", "invalidated"}:
        return False
    if normalized.get("expires_at") is None:
        return True
    if now is None:
        now = datetime.now(timezone.utc)

    try:
        expires_at = datetime.fromisoformat(str(normalized.get("expires_at")))
    except ValueError:
        return True

    return now < expires_at


def is_expired(record: Optional[Dict[str, Any]], *, now: Optional[datetime] = None) -> bool:
    normalized = normalize_evidence_record(record)
    if normalized.get("state_type") in {"invalidated", "expired"}:
        return True
    if normalized.get("expires_at") is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)

    try:
        expires_at = datetime.fromisoformat(str(normalized.get("expires_at")))
    except ValueError:
        return False

    return now >= expires_at


def render_evidence_for_prompt(store: Dict[str, Any], *, key: str) -> str:
    record = get_evidence(store, key)
    state_type = record.get("state_type", "unknown")
    value = record.get("value")

    if state_type == "unknown":
        return f"{key}: unknown"
    if state_type == "verified":
        return f"{key}: verified as {value}"
    if state_type == "observed":
        return f"{key}: observed as {value}"
    if state_type == "configured":
        return f"{key}: configured as {value}"
    if state_type == "declared":
        return f"{key}: reported as {value}"
    if state_type == "inferred":
        return f"{key}: inferred as {value}"
    if state_type == "invalidated":
        return f"{key}: invalidated"
    if state_type == "expired":
        return f"{key}: expired"
    return f"{key}: {value}"


def render_prompt_summary(store: Dict[str, Any]) -> str:
    facts = store.get("facts", {}) if isinstance(store, dict) else {}
    if not isinstance(facts, dict) or not facts:
        return "Evidence Summary\n\nNo evidence recorded."

    lines = ["Evidence Summary"]
    for key in sorted(facts):
        lines.append("")
        lines.append(render_evidence_for_prompt(store, key=key))
    return "\n".join(lines)
