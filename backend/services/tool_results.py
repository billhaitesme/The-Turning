from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy
from typing import Any, Dict, List, Optional

from services.tool_contracts import (
    TOOL_RESULTS_PATH,
    empty_tool_result_store,
    save_store,
    validate_tool_result,
)
from services.tool_result_store import (
    append_tool_result,
    empty_tool_result_store as _empty_tool_result_store,
    get_tool_result,
    list_tool_results,
    load_tool_result_store as _load_tool_result_store,
    save_tool_result_store as _save_tool_result_store,
)


def load_tool_result_store(path: Path = TOOL_RESULTS_PATH) -> Dict[str, Any]:
    return _load_tool_result_store(path)


def save_tool_result_store(store: Dict[str, Any], path: Path = TOOL_RESULTS_PATH) -> None:
    _save_tool_result_store(store, path)


def create_tool_result(
    *,
    request_id: str,
    tool_name: str,
    status: str,
    success: bool,
    started_at: str,
    completed_at: str,
    duration_ms: float,
    output: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    evidence_candidates: Optional[List[Dict[str, Any]]] = None,
    side_effects_observed: Optional[List[Dict[str, Any]]] = None,
    executor: str = "local_adapter",
    execution_mode: str = "live",
) -> Dict[str, Any]:
    return validate_tool_result(
        {
            "request_id": request_id,
            "tool_name": tool_name,
            "status": status,
            "success": success,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": float(duration_ms),
            "output": deepcopy(output or {}),
            "error": deepcopy(error),
            "evidence_candidates": deepcopy(evidence_candidates or []),
            "side_effects_observed": deepcopy(side_effects_observed or []),
            "executor": executor,
            "execution_mode": execution_mode,
        }
    )


def tool_result_to_evidence_candidates(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    from services.tool_evidence_bridge import tool_result_to_evidence_candidates as _tool_result_to_evidence_candidates

    return _tool_result_to_evidence_candidates(result)


def record_tool_result(result: Dict[str, Any], path: Path = TOOL_RESULTS_PATH) -> Dict[str, Any]:
    store = load_tool_result_store(path)
    append_tool_result(result, store=store)
    save_tool_result_store(store, path)
    return store
