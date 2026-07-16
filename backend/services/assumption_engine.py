from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_ASSUMPTION_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "assumptions.json"
VALID_ASSUMPTION_STATUSES = {"known", "unknown", "assumed", "invalidated"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_assumption_store() -> Dict[str, Any]:
    return {"version": 1, "assumptions": []}


def _normalize_store(store: Any) -> Dict[str, Any]:
    if not isinstance(store, dict):
        return empty_assumption_store()

    normalized = deepcopy(store)
    if not isinstance(normalized.get("version"), int):
        normalized["version"] = 1
    if not isinstance(normalized.get("assumptions"), list):
        normalized["assumptions"] = []

    cleaned: List[Dict[str, Any]] = []
    for item in normalized["assumptions"]:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown").lower()
        item["status"] = status if status in VALID_ASSUMPTION_STATUSES else "unknown"
        if not isinstance(item.get("supporting_evidence"), list):
            item["supporting_evidence"] = []
        if not isinstance(item.get("invalidated_by"), list):
            item["invalidated_by"] = []
        try:
            item["confidence"] = max(0.0, min(1.0, float(item.get("confidence", 0.0))))
        except (TypeError, ValueError):
            item["confidence"] = 0.0
        cleaned.append(item)
    normalized["assumptions"] = cleaned
    return normalized


def load_assumption_store(path: Path = DEFAULT_ASSUMPTION_STORE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return empty_assumption_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_assumption_store()
    return _normalize_store(data)


def save_assumption_store(store: Dict[str, Any], path: Path = DEFAULT_ASSUMPTION_STORE_PATH) -> None:
    normalized = _normalize_store(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


def create_assumption(
    *,
    assumption_id: str,
    statement: str,
    status: str = "assumed",
    confidence: float = 0.4,
    supporting_evidence: Optional[List[str]] = None,
    invalidated_by: Optional[List[str]] = None,
    goal_id: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> Dict[str, Any]:
    now = utc_now_iso()
    normalized_status = str(status or "assumed").lower()
    if normalized_status not in VALID_ASSUMPTION_STATUSES:
        normalized_status = "unknown"

    return {
        "id": assumption_id,
        "statement": statement,
        "status": normalized_status,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "supporting_evidence": list(supporting_evidence or []),
        "invalidated_by": list(invalidated_by or []),
        "goal_id": goal_id,
        "plan_id": plan_id,
        "created_at": now,
        "updated_at": now,
    }


def upsert_assumption(store: Dict[str, Any], assumption: Dict[str, Any]) -> Dict[str, Any]:
    updated = _normalize_store(store)
    incoming = deepcopy(assumption)
    assumption_id = str(incoming.get("id") or "").strip()
    if not assumption_id:
        return updated

    incoming.setdefault("updated_at", utc_now_iso())
    replaced = False
    for index, item in enumerate(updated["assumptions"]):
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") != assumption_id:
            continue
        updated["assumptions"][index] = incoming
        replaced = True
        break

    if not replaced:
        updated["assumptions"].append(incoming)

    return _normalize_store(updated)


def list_assumptions(store: Dict[str, Any], *, status: Optional[str] = None, goal_id: Optional[str] = None) -> List[Dict[str, Any]]:
    assumptions = store.get("assumptions", []) if isinstance(store, dict) else []
    result: List[Dict[str, Any]] = []
    for item in assumptions:
        if not isinstance(item, dict):
            continue
        if status is not None and str(item.get("status") or "") != str(status):
            continue
        if goal_id is not None and str(item.get("goal_id") or "") != str(goal_id):
            continue
        result.append(deepcopy(item))
    return result


def invalidate_assumption(
    store: Dict[str, Any],
    *,
    assumption_id: str,
    invalidated_by: Optional[List[str]] = None,
) -> Dict[str, Any]:
    updated = _normalize_store(store)
    for item in updated["assumptions"]:
        if str(item.get("id") or "") != str(assumption_id):
            continue
        item["status"] = "invalidated"
        item["invalidated_by"] = list(invalidated_by or [])
        item["confidence"] = min(float(item.get("confidence", 0.0)), 0.2)
        item["updated_at"] = utc_now_iso()
    return updated


def verify_assumption(store: Dict[str, Any], *, assumption_id: str, supporting_evidence: Optional[List[str]] = None) -> Dict[str, Any]:
    updated = _normalize_store(store)
    for item in updated["assumptions"]:
        if str(item.get("id") or "") != str(assumption_id):
            continue
        item["status"] = "known"
        item["supporting_evidence"] = list(supporting_evidence or item.get("supporting_evidence") or [])
        item["confidence"] = max(float(item.get("confidence", 0.0)), 0.8)
        item["updated_at"] = utc_now_iso()
    return updated
