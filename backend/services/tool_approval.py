from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.tool_contracts import (
    TOOL_APPROVALS_PATH,
    TOOL_REQUESTS_PATH,
    empty_tool_approval_store,
    empty_tool_request_store,
    request_arguments_hash,
    save_store,
    utc_now_iso,
    validate_tool_request,
)


def _load_store(path: Path, key: str) -> Dict[str, Any]:
    if not path.exists():
        return empty_tool_request_store() if key == "requests" else empty_tool_approval_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_tool_request_store() if key == "requests" else empty_tool_approval_store()
    if not isinstance(data, dict):
        return empty_tool_request_store() if key == "requests" else empty_tool_approval_store()
    if not isinstance(data.get("version"), int):
        data["version"] = 1
    if not isinstance(data.get(key), list):
        data[key] = []
    return data


def load_tool_request_store(path: Path = TOOL_REQUESTS_PATH) -> Dict[str, Any]:
    return _load_store(path, "requests")


def save_tool_request_store(store: Dict[str, Any], path: Path = TOOL_REQUESTS_PATH) -> None:
    save_store(store, path, "requests")


def load_tool_approval_store(path: Path = TOOL_APPROVALS_PATH) -> Dict[str, Any]:
    return _load_store(path, "approvals")


def save_tool_approval_store(store: Dict[str, Any], path: Path = TOOL_APPROVALS_PATH) -> None:
    save_store(store, path, "approvals")


def list_tool_requests(store: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    request_store = load_tool_request_store() if store is None else store
    return [deepcopy(item) for item in request_store.get("requests", []) if isinstance(item, dict)]


def get_tool_request(request_id: str, store: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    for item in list_tool_requests(store):
        if str(item.get("request_id") or "") == str(request_id):
            return item
    return None


def upsert_tool_request(request: Dict[str, Any], store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    normalized = validate_tool_request(request)
    request_store = load_tool_request_store() if store is None else store
    request_store.setdefault("version", 1)
    request_store.setdefault("requests", [])

    replaced = False
    for index, existing in enumerate(request_store["requests"]):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("request_id") or "") != normalized["request_id"]:
            continue
        request_store["requests"][index] = deepcopy(normalized)
        replaced = True
        break

    if not replaced:
        request_store["requests"].append(deepcopy(normalized))

    if store is None:
        save_tool_request_store(request_store)
    return normalized


def list_tool_approvals(store: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    approval_store = load_tool_approval_store() if store is None else store
    return [deepcopy(item) for item in approval_store.get("approvals", []) if isinstance(item, dict)]


def get_tool_approval(approval_id: str, store: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    for item in list_tool_approvals(store):
        if str(item.get("approval_id") or "") == str(approval_id):
            return item
    return None


def _upsert_tool_approval(approval: Dict[str, Any], store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    approval_store = load_tool_approval_store() if store is None else store
    approval_store.setdefault("version", 1)
    approval_store.setdefault("approvals", [])

    replaced = False
    for index, existing in enumerate(approval_store["approvals"]):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("approval_id") or "") != str(approval.get("approval_id") or ""):
            continue
        approval_store["approvals"][index] = deepcopy(approval)
        replaced = True
        break

    if not replaced:
        approval_store["approvals"].append(deepcopy(approval))

    if store is None:
        save_tool_approval_store(approval_store)
    return deepcopy(approval)


def _parse_iso_datetime(value: str) -> datetime:
    cleaned = str(value or "").replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


def _default_ttl_seconds() -> int:
    try:
        return max(1, int(os.getenv("TOOL_APPROVAL_TTL_SECONDS", "300")))
    except Exception:
        return 300


def create_approval_request(
    request: Dict[str, Any],
    *,
    approval_store: Optional[Dict[str, Any]] = None,
    request_store: Optional[Dict[str, Any]] = None,
    ttl_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    validated_request = validate_tool_request(request)
    request_store_obj = load_tool_request_store() if request_store is None else request_store
    approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds or _default_ttl_seconds())

    approval = {
        "approval_id": validated_request.get("approval_id") or f"approval-{validated_request['request_id']}",
        "request_id": validated_request["request_id"],
        "status": "pending",
        "approved_by": None,
        "approved_at": None,
        "expires_at": expires_at.isoformat(),
        "scope": {
            "tool_name": validated_request["tool_name"],
            "arguments_hash": request_arguments_hash(validated_request.get("arguments") or {}),
        },
        "created_at": utc_now_iso(),
        "consumed_at": None,
        "revoked_at": None,
        "revoked_reason": None,
    }

    validated_request["approval_id"] = approval["approval_id"]
    validated_request["status"] = "awaiting_approval"
    upsert_tool_request(validated_request, store=request_store_obj)

    _upsert_tool_approval(approval, store=approval_store_obj)  # Prevent overwriting store object

    if request_store is None:
        save_tool_request_store(request_store_obj)
    if approval_store is None:
        save_tool_approval_store(approval_store_obj)
    return deepcopy(approval)


def approve_request(
    request_id: str,
    *,
    approved_by: Optional[str] = None,
    approval_store: Optional[Dict[str, Any]] = None,
    request_store: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    request_store_obj = load_tool_request_store() if request_store is None else request_store
    approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store
    request = get_tool_request(request_id, request_store_obj)
    if not request:
        raise ValueError("Tool request not found.")

    approval = next((item for item in list_tool_approvals(approval_store_obj) if str(item.get("request_id") or "") == str(request_id)), None)
    if not approval:
        approval = create_approval_request(request, approval_store=approval_store_obj, request_store=request_store_obj)
        approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store_obj

    if approval.get("consumed_at"):
        raise ValueError("Approval has already been consumed.")

    if approval.get("status") in {"expired", "rejected", "revoked"}:
        raise ValueError(f"Approval is not approvable in state {approval.get('status')}.")

    approval["status"] = "approved"
    approval["approved_by"] = approved_by or "user"
    approval["approved_at"] = utc_now_iso()
    _upsert_tool_approval(approval, store=approval_store_obj)  # Prevent overwriting store object

    request["status"] = "approved"
    upsert_tool_request(request, store=request_store_obj)

    if request_store is None:
        save_tool_request_store(request_store_obj)
    if approval_store is None:
        save_tool_approval_store(approval_store_obj)
    return deepcopy(approval)


def reject_request(
    request_id: str,
    *,
    rejected_by: Optional[str] = None,
    approval_store: Optional[Dict[str, Any]] = None,
    request_store: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    request_store_obj = load_tool_request_store() if request_store is None else request_store
    approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store
    request = get_tool_request(request_id, request_store_obj)
    if not request:
        raise ValueError("Tool request not found.")

    approval = next((item for item in list_tool_approvals(approval_store_obj) if str(item.get("request_id") or "") == str(request_id)), None)
    if not approval:
        approval = create_approval_request(request, approval_store=approval_store_obj, request_store=request_store_obj)

    approval["status"] = "rejected"
    approval["approved_by"] = rejected_by or "user"
    approval["approved_at"] = utc_now_iso()
    _upsert_tool_approval(approval, store=approval_store_obj)

    request["status"] = "rejected"
    upsert_tool_request(request, store=request_store_obj)

    if request_store is None:
        save_tool_request_store(request_store_obj)
    if approval_store is None:
        save_tool_approval_store(approval_store_obj)
    return deepcopy(approval)


def revoke_approval(
    approval_id: str,
    *,
    approval_store: Optional[Dict[str, Any]] = None,
    request_store: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    request_store_obj = load_tool_request_store() if request_store is None else request_store
    approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store
    approval = get_tool_approval(approval_id, approval_store_obj)
    if not approval:
        raise ValueError("Approval not found.")

    approval["status"] = "revoked"
    approval["revoked_at"] = utc_now_iso()
    approval["revoked_reason"] = reason or "revoked"
    _upsert_tool_approval(approval, store=approval_store_obj)

    request = get_tool_request(approval.get("request_id") or "", request_store_obj)
    if request:
        request["status"] = "cancelled"
        upsert_tool_request(request, store=request_store_obj)

    if request_store is None:
        save_tool_request_store(request_store_obj)
    if approval_store is None:
        save_tool_approval_store(approval_store_obj)
    return deepcopy(approval)


def expire_approvals(
    *,
    approval_store: Optional[Dict[str, Any]] = None,
    request_store: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    request_store_obj = load_tool_request_store() if request_store is None else request_store
    approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store
    current_time = now or datetime.now(timezone.utc)
    changed = False

    for approval in approval_store_obj.get("approvals", []):
        if not isinstance(approval, dict):
            continue
        if approval.get("status") not in {"pending", "approved"}:
            continue
        try:
            expires_at = _parse_iso_datetime(str(approval.get("expires_at") or ""))
        except Exception:
            continue
        if expires_at > current_time:
            continue
        approval["status"] = "expired"
        changed = True
        request = get_tool_request(approval.get("request_id") or "", request_store_obj)
        if request:
            request["status"] = "expired"
            upsert_tool_request(request, store=request_store_obj)

    if changed:
        if request_store is None:
            save_tool_request_store(request_store_obj)
        if approval_store is None:
            save_tool_approval_store(approval_store_obj)
    return approval_store_obj


def validate_approval_for_request(request: Dict[str, Any], approval_store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    validated_request = validate_tool_request(request)
    approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store
    approval = next(
        (item for item in list_tool_approvals(approval_store_obj) if str(item.get("request_id") or "") == validated_request["request_id"]),
        None,
    )
    if not approval:
        raise ValueError("Approval does not exist for request.")
    if approval.get("status") != "approved":
        raise ValueError("Approval is not approved.")
    if approval.get("consumed_at"):
        raise ValueError("Approval has already been consumed.")

    try:
        expires_at = _parse_iso_datetime(str(approval.get("expires_at") or ""))
    except Exception as exc:
        raise ValueError("Approval expiration is invalid.") from exc

    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("Approval has expired.")

    scope = approval.get("scope") or {}
    if str(scope.get("tool_name") or "") != validated_request["tool_name"]:
        raise ValueError("Approval tool name does not match request.")
    if str(scope.get("arguments_hash") or "") != request_arguments_hash(validated_request.get("arguments") or {}):
        raise ValueError("Approval arguments do not match request.")

    return deepcopy(approval)


def consume_approval(
    approval_id: str,
    *,
    approval_store: Optional[Dict[str, Any]] = None,
    request_store: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    request_store_obj = load_tool_request_store() if request_store is None else request_store
    approval_store_obj = load_tool_approval_store() if approval_store is None else approval_store
    approval = get_tool_approval(approval_id, approval_store_obj)
    if not approval:
        raise ValueError("Approval not found.")

    approval["status"] = "revoked"
    approval["consumed_at"] = utc_now_iso()
    approval["revoked_at"] = approval["consumed_at"]
    approval["revoked_reason"] = "consumed"
    _upsert_tool_approval(approval, store=approval_store_obj)

    request = get_tool_request(approval.get("request_id") or "", request_store_obj)
    if request:
        request["approval_id"] = approval.get("approval_id")
        if request.get("status") == "executing":
            request["status"] = "completed"
        upsert_tool_request(request, store=request_store_obj)

    if request_store is None:
        save_tool_request_store(request_store_obj)
    if approval_store is None:
        save_tool_approval_store(approval_store_obj)
    return deepcopy(approval)
