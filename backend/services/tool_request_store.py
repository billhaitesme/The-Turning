from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.tool_contracts import TOOL_REQUESTS_PATH, build_tool_request, empty_tool_request_store, load_store, save_store, validate_tool_request


def empty_tool_request_store() -> Dict[str, Any]:
    return {"version": 1, "requests": []}


def load_tool_request_store(path: Path = TOOL_REQUESTS_PATH) -> Dict[str, Any]:
    return load_store(path, "requests")


def save_tool_request_store(store: Dict[str, Any], path: Path = TOOL_REQUESTS_PATH) -> None:
    save_store(store, path, "requests")


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

    merged = deepcopy(normalized)
    for index, existing in enumerate(request_store["requests"]):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("request_id") or "") != normalized["request_id"]:
            continue
        merged = {**deepcopy(existing), **merged}
        request_store["requests"][index] = merged
        break
    else:
        request_store["requests"].append(merged)

    if store is None:
        save_tool_request_store(request_store)
    return deepcopy(merged)


def update_request_status(
    request_id: str,
    status: str,
    *,
    store: Optional[Dict[str, Any]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    request_store = load_tool_request_store() if store is None else store
    request_store.setdefault("version", 1)
    request_store.setdefault("requests", [])

    for index, existing in enumerate(request_store["requests"]):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("request_id") or "") != str(request_id):
            continue
        updated = {**deepcopy(existing), **deepcopy(extra_fields or {})}
        updated["status"] = str(status)
        updated.setdefault("updated_at", existing.get("updated_at") or existing.get("created_at"))
        request_store["requests"][index] = updated
        if store is None:
            save_tool_request_store(request_store)
        return deepcopy(updated)

    raise ValueError("Tool request not found.")
