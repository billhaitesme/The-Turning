from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_PLAN_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "plans.json"

ACTIVE_PLAN_STATUSES = {"active", "validated", "proposed", "blocked"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_plan_store() -> Dict[str, Any]:
    return {"version": 1, "plans": []}


def _normalize_plan_store(store: Any) -> Dict[str, Any]:
    if not isinstance(store, dict):
        return empty_plan_store()

    normalized = deepcopy(store)
    if not isinstance(normalized.get("plans"), list):
        normalized["plans"] = []
    if not isinstance(normalized.get("version"), int):
        normalized["version"] = 1

    return normalized


def load_plan_store(path: Path = DEFAULT_PLAN_STORE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return empty_plan_store()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_plan_store()

    return _normalize_plan_store(data)


def save_plan_store(store: Dict[str, Any], path: Path = DEFAULT_PLAN_STORE_PATH) -> None:
    normalized = _normalize_plan_store(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


def get_plan(store: Dict[str, Any], plan_id: str) -> Optional[Dict[str, Any]]:
    plans = store.get("plans", []) if isinstance(store, dict) else []
    for plan in plans:
        if isinstance(plan, dict) and str(plan.get("id")) == str(plan_id):
            return deepcopy(plan)
    return None


def list_plans(
    store: Dict[str, Any],
    *,
    status: Optional[str] = None,
    goal_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    plans = store.get("plans", []) if isinstance(store, dict) else []
    result: List[Dict[str, Any]] = []

    for plan in plans:
        if not isinstance(plan, dict):
            continue
        if status is not None and str(plan.get("status")) != status:
            continue
        if goal_id is not None and str(plan.get("goal_id")) != str(goal_id):
            continue
        result.append(deepcopy(plan))

    return result


def find_active_plan_for_goal(store: Dict[str, Any], goal_id: str) -> Optional[Dict[str, Any]]:
    candidates = [
        plan
        for plan in list_plans(store, goal_id=goal_id)
        if str(plan.get("status") or "").lower() in ACTIVE_PLAN_STATUSES
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("id") or "")), reverse=True)
    return deepcopy(candidates[0])


def upsert_plan(store: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    updated = _normalize_plan_store(store)
    incoming = deepcopy(plan)
    plan_id = str(incoming.get("id") or "").strip()
    if not plan_id:
        return updated

    incoming.setdefault("updated_at", utc_now_iso())
    incoming.setdefault("version", 1)

    replaced = False
    for index, existing in enumerate(updated["plans"]):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("id")) != plan_id:
            continue
        updated["plans"][index] = incoming
        replaced = True
        break

    if not replaced:
        updated["plans"].append(incoming)

    # Only one active plan is allowed per goal. Archive older active plans.
    incoming_status = str(incoming.get("status") or "").lower()
    goal_id = incoming.get("goal_id")
    if goal_id and incoming_status == "active":
        for existing in updated["plans"]:
            if not isinstance(existing, dict):
                continue
            if str(existing.get("id")) == plan_id:
                continue
            if str(existing.get("goal_id")) != str(goal_id):
                continue
            if str(existing.get("status") or "").lower() in ACTIVE_PLAN_STATUSES:
                existing["status"] = "archived"
                existing["updated_at"] = utc_now_iso()

    return updated


def archive_plan(store: Dict[str, Any], plan_id: str) -> Dict[str, Any]:
    updated = _normalize_plan_store(store)
    for plan in updated["plans"]:
        if not isinstance(plan, dict):
            continue
        if str(plan.get("id")) != str(plan_id):
            continue
        plan["status"] = "archived"
        plan["updated_at"] = utc_now_iso()
    return updated


def supersede_plan(
    store: Dict[str, Any],
    *,
    old_plan_id: str,
    new_plan: Dict[str, Any],
) -> Dict[str, Any]:
    updated = _normalize_plan_store(store)
    replacement = deepcopy(new_plan)
    replacement_id = str(replacement.get("id") or "").strip()
    if not replacement_id:
        return updated

    replacement.setdefault("supersedes", old_plan_id)
    replacement.setdefault("status", "active")
    replacement["updated_at"] = utc_now_iso()

    found_old = False
    for plan in updated["plans"]:
        if not isinstance(plan, dict):
            continue
        if str(plan.get("id")) != str(old_plan_id):
            continue
        plan["status"] = "superseded"
        plan["superseded_by"] = replacement_id
        plan["updated_at"] = utc_now_iso()
        found_old = True

    updated = upsert_plan(updated, replacement)

    if not found_old:
        # Keep a stable store even if old id was missing.
        return updated

    return updated
