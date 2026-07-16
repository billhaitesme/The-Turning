from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.tool_contracts import TOOL_RESULTS_PATH, empty_tool_result_store, load_store, save_store, validate_tool_result


def empty_tool_result_store() -> Dict[str, Any]:
    return {"version": 1, "results": []}


def load_tool_result_store(path: Path = TOOL_RESULTS_PATH) -> Dict[str, Any]:
    return load_store(path, "results")


def save_tool_result_store(store: Dict[str, Any], path: Path = TOOL_RESULTS_PATH) -> None:
    save_store(store, path, "results")


def list_tool_results(store: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    result_store = load_tool_result_store() if store is None else store
    return [deepcopy(item) for item in result_store.get("results", []) if isinstance(item, dict)]


def get_tool_result(request_id: str, store: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    results = list_tool_results(store)
    for item in reversed(results):
        if str(item.get("request_id") or "") == str(request_id):
            return item
    return None


def append_tool_result(result: Dict[str, Any], store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    validated = validate_tool_result(result)
    result_store = load_tool_result_store() if store is None else store
    result_store.setdefault("version", 1)
    result_store.setdefault("results", [])
    result_store["results"].append(deepcopy(validated))
    if store is None:
        save_tool_result_store(result_store)
    return deepcopy(validated)
