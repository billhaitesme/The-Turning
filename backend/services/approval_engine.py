from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_APPROVAL_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "approvals.json"
APPROVAL_STATUSES = {"proposed", "recommended", "approved", "implemented", "archived"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_approval_store() -> Dict[str, Any]:
    return {"version": 1, "approvals": []}


def _normalize_store(store: Any) -> Dict[str, Any]:
    if not isinstance(store, dict):
        return empty_approval_store()
    normalized = deepcopy(store)
    if not isinstance(normalized.get("version"), int):
        normalized["version"] = 1
    if not isinstance(normalized.get("approvals"), list):
        normalized["approvals"] = []
    return normalized


def load_approval_store(path: Path = DEFAULT_APPROVAL_STORE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return empty_approval_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_approval_store()
    return _normalize_store(data)


def save_approval_store(store: Dict[str, Any], path: Path = DEFAULT_APPROVAL_STORE_PATH) -> None:
    normalized = _normalize_store(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


def create_approval(
    *,
    approval_id: str,
    goal_id: str,
    plan_id: str,
    status: str = "recommended",
    rationale: str = "",
    approved_by: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_status = str(status or "recommended").lower()
    if normalized_status not in APPROVAL_STATUSES:
        normalized_status = "proposed"
    now = utc_now_iso()
    return {
        "id": approval_id,
        "goal_id": goal_id,
        "plan_id": plan_id,
        "status": normalized_status,
        "rationale": rationale,
        "approved_by": approved_by,
        "created_at": now,
        "updated_at": now,
    }


def upsert_approval(store: Dict[str, Any], approval: Dict[str, Any]) -> Dict[str, Any]:
    updated = _normalize_store(store)
    incoming = deepcopy(approval)
    approval_id = str(incoming.get("id") or "").strip()
    if not approval_id:
        return updated
    incoming.setdefault("updated_at", utc_now_iso())

    replaced = False
    for index, item in enumerate(updated["approvals"]):
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") != approval_id:
            continue
        updated["approvals"][index] = incoming
        replaced = True
        break

    if not replaced:
        updated["approvals"].append(incoming)

    return updated


def set_approval_status(
    store: Dict[str, Any],
    *,
    approval_id: str,
    status: str,
    approved_by: Optional[str] = None,
) -> Dict[str, Any]:
    updated = _normalize_store(store)
    normalized_status = str(status or "").lower()
    if normalized_status not in APPROVAL_STATUSES:
        return updated

    for item in updated["approvals"]:
        if str(item.get("id") or "") != str(approval_id):
            continue
        item["status"] = normalized_status
        if approved_by is not None:
            item["approved_by"] = approved_by
        item["updated_at"] = utc_now_iso()

    return updated
