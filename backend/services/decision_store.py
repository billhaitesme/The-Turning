from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DECISION_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "decisions.json"


def empty_decision_store() -> Dict[str, Any]:
    return {"version": 1, "decisions": []}


def _normalize_store(store: Any) -> Dict[str, Any]:
    if not isinstance(store, dict):
        return empty_decision_store()

    normalized = deepcopy(store)
    if not isinstance(normalized.get("version"), int):
        normalized["version"] = 1
    if not isinstance(normalized.get("decisions"), list):
        normalized["decisions"] = []
    return normalized


def load_decision_store(path: Path = DEFAULT_DECISION_STORE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return empty_decision_store()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_decision_store()

    return _normalize_store(data)


def save_decision_store(store: Dict[str, Any], path: Path = DEFAULT_DECISION_STORE_PATH) -> None:
    normalized = _normalize_store(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


def get_decision(store: Dict[str, Any], decision_id: str) -> Optional[Dict[str, Any]]:
    for decision in store.get("decisions", []) if isinstance(store, dict) else []:
        if isinstance(decision, dict) and str(decision.get("id")) == str(decision_id):
            return deepcopy(decision)
    return None


def list_decisions(
    store: Dict[str, Any],
    *,
    status: Optional[str] = None,
    goal_id: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    decisions = store.get("decisions", []) if isinstance(store, dict) else []
    result: List[Dict[str, Any]] = []

    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        if status is not None and str(decision.get("status")) != status:
            continue
        if goal_id is not None and str(decision.get("goal_id")) != str(goal_id):
            continue
        if plan_id is not None and str(decision.get("plan_id")) != str(plan_id):
            continue
        result.append(deepcopy(decision))

    return result


def upsert_decision(store: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    updated = _normalize_store(store)
    incoming = deepcopy(decision)
    decision_id = str(incoming.get("id") or "").strip()
    if not decision_id:
        return updated

    replaced = False
    for index, existing in enumerate(updated["decisions"]):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("id")) != decision_id:
            continue
        updated["decisions"][index] = incoming
        replaced = True
        break

    if not replaced:
        updated["decisions"].append(incoming)

    return updated


def supersede_decision_in_store(
    store: Dict[str, Any],
    *,
    old_decision_id: str,
    new_decision: Dict[str, Any],
) -> Dict[str, Any]:
    updated = _normalize_store(store)
    replacement = deepcopy(new_decision)
    replacement_id = str(replacement.get("id") or "").strip()
    if not replacement_id:
        return updated

    replacement.setdefault("supersedes", old_decision_id)
    replacement.setdefault("status", "active")

    for decision in updated["decisions"]:
        if not isinstance(decision, dict):
            continue
        if str(decision.get("id")) != str(old_decision_id):
            continue
        decision["status"] = "superseded"
        decision["superseded_by"] = replacement_id

    return upsert_decision(updated, replacement)
