from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.tool_contracts import (
    TOOL_RESULTS_PATH,
    empty_tool_result_store,
    save_store,
    utc_now_iso,
    validate_tool_result,
)


def load_tool_result_store(path: Path = TOOL_RESULTS_PATH) -> Dict[str, Any]:
    if not path.exists():
        return empty_tool_result_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_tool_result_store()
    if not isinstance(data, dict):
        return empty_tool_result_store()
    if not isinstance(data.get("version"), int):
        data["version"] = 1
    if not isinstance(data.get("results"), list):
        data["results"] = []
    return data


def save_tool_result_store(store: Dict[str, Any], path: Path = TOOL_RESULTS_PATH) -> None:
    save_store(store, path, "results")


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
    validated = validate_tool_result(result)
    if str(validated.get("execution_mode") or "live") == "dry_run":
        return []

    status = str(validated.get("status") or "")
    if status != "completed" and not validated.get("success"):
        return [
            {
                "candidate_id": f"tool-evidence-{uuid.uuid4().hex}",
                "kind": "observed_failure",
                "state": "proposed",
                "request_id": validated["request_id"],
                "tool_name": validated["tool_name"],
                "adapter_name": validated["executor"],
                "created_at": validated["completed_at"],
                "observed_at": validated["completed_at"],
                "output": deepcopy(validated.get("output") or {}),
                "error": deepcopy(validated.get("error")),
                "side_effects_observed": deepcopy(validated.get("side_effects_observed") or []),
                "provenance": {
                    "request_id": validated["request_id"],
                    "tool_name": validated["tool_name"],
                    "adapter_name": validated["executor"],
                    "started_at": validated["started_at"],
                    "completed_at": validated["completed_at"],
                    "duration_ms": validated["duration_ms"],
                },
            }
        ]

    if status != "completed" or not validated.get("success"):
        return []

    return [
        {
            "candidate_id": f"tool-evidence-{uuid.uuid4().hex}",
            "kind": "verified_tool_result",
            "state": "proposed",
            "request_id": validated["request_id"],
            "tool_name": validated["tool_name"],
            "adapter_name": validated["executor"],
            "created_at": validated["completed_at"],
            "observed_at": validated["completed_at"],
            "output": deepcopy(validated.get("output") or {}),
            "error": deepcopy(validated.get("error")),
            "side_effects_observed": deepcopy(validated.get("side_effects_observed") or []),
            "provenance": {
                "request_id": validated["request_id"],
                "tool_name": validated["tool_name"],
                "adapter_name": validated["executor"],
                "started_at": validated["started_at"],
                "completed_at": validated["completed_at"],
                "duration_ms": validated["duration_ms"],
            },
        }
    ]


def record_tool_result(result: Dict[str, Any], path: Path = TOOL_RESULTS_PATH) -> Dict[str, Any]:
    store = load_tool_result_store(path)
    store["results"].append(validate_tool_result(result))
    save_tool_result_store(store, path)
    return store
