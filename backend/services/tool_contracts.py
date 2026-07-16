from __future__ import annotations

import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

VALID_TOOL_CATEGORIES = {"diagnostic", "inspection", "verification", "maintenance", "mutation"}
VALID_TOOL_RISK_LEVELS = {"low", "medium", "high", "critical"}
VALID_TOOL_REQUEST_STATUSES = {"proposed", "awaiting_approval", "approved", "rejected", "executing", "completed", "failed", "expired", "cancelled"}
VALID_APPROVAL_STATUSES = {"pending", "approved", "rejected", "expired", "revoked"}
VALID_TOOL_RESULT_STATUSES = {"completed", "failed", "endpoint_mismatch"}

TOOL_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TOOL_REQUESTS_PATH = TOOL_DATA_DIR / "tool_requests.json"
TOOL_APPROVALS_PATH = TOOL_DATA_DIR / "tool_approvals.json"
TOOL_RESULTS_PATH = TOOL_DATA_DIR / "tool_results.json"


class ToolAdapter(ABC):
    @abstractmethod
    def describe(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_tool_request_store() -> Dict[str, Any]:
    return {"version": 1, "requests": []}


def empty_tool_approval_store() -> Dict[str, Any]:
    return {"version": 1, "approvals": []}


def empty_tool_result_store() -> Dict[str, Any]:
    return {"version": 1, "results": []}


def _normalize_store(store: Any, key: str) -> Dict[str, Any]:
    if not isinstance(store, dict):
        if key == "requests":
            return empty_tool_request_store()
        if key == "approvals":
            return empty_tool_approval_store()
        return empty_tool_result_store()
    normalized = deepcopy(store)
    if not isinstance(normalized.get("version"), int):
        normalized["version"] = 1
    if not isinstance(normalized.get(key), list):
        normalized[key] = []
    return normalized


def load_store(path: Path, key: str) -> Dict[str, Any]:
    if not path.exists():
        return _normalize_store(None, key)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _normalize_store(None, key)
    return _normalize_store(data, key)


def save_store(store: Dict[str, Any], path: Path, key: str) -> None:
    normalized = _normalize_store(store, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


def request_arguments_hash(arguments: Dict[str, Any]) -> str:
    payload = json.dumps(arguments or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_tool_request(
    *,
    tool_name: str,
    arguments: Optional[Dict[str, Any]],
    requested_by: str,
    session_id: str,
    goal_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "request_id": f"toolreq-{uuid.uuid4().hex}",
        "tool_name": str(tool_name),
        "arguments": deepcopy(arguments or {}),
        "requested_by": str(requested_by),
        "session_id": str(session_id),
        "goal_id": goal_id,
        "plan_id": plan_id,
        "decision_id": decision_id,
        "approval_id": approval_id,
        "created_at": utc_now_iso(),
        "status": "proposed",
    }


def validate_tool_definition(tool: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool, dict):
        raise ValueError("Tool definition must be a dictionary.")

    required_keys = [
        "name",
        "version",
        "description",
        "category",
        "risk_level",
        "requires_approval",
        "supports_dry_run",
        "input_schema",
        "output_schema",
        "side_effects",
        "allowed_scopes",
        "enabled",
    ]
    missing = [key for key in required_keys if key not in tool]
    if missing:
        raise ValueError(f"Tool definition missing required keys: {', '.join(missing)}")

    name = str(tool.get("name") or "").strip()
    if not name:
        raise ValueError("Tool name is required.")

    version = tool.get("version")
    if not isinstance(version, int) or version < 1:
        raise ValueError("Tool version must be a positive integer.")

    description = str(tool.get("description") or "").strip()
    if not description:
        raise ValueError("Tool description is required.")

    category = str(tool.get("category") or "").strip()
    if category not in VALID_TOOL_CATEGORIES:
        raise ValueError(f"Unsupported tool category: {category}")

    risk_level = str(tool.get("risk_level") or "").strip()
    if risk_level not in VALID_TOOL_RISK_LEVELS:
        raise ValueError(f"Unsupported tool risk level: {risk_level}")
    if risk_level == "critical":
        raise ValueError("Critical tools are not supported in Epoch VIII.")

    requires_approval = tool.get("requires_approval")
    supports_dry_run = tool.get("supports_dry_run")
    enabled = tool.get("enabled")
    if not isinstance(requires_approval, bool):
        raise ValueError("Tool approval requirement must be declared as a boolean.")
    if not isinstance(supports_dry_run, bool):
        raise ValueError("Tool dry-run support must be declared as a boolean.")
    if not isinstance(enabled, bool):
        raise ValueError("Tool enabled state must be declared as a boolean.")

    if category == "mutation" and not requires_approval:
        raise ValueError("Mutation tools must require approval.")

    input_schema = tool.get("input_schema")
    output_schema = tool.get("output_schema")
    if not isinstance(input_schema, dict):
        raise ValueError("Tool input schema must be a dictionary.")
    if not isinstance(output_schema, dict):
        raise ValueError("Tool output schema must be a dictionary.")

    side_effects = tool.get("side_effects")
    if not isinstance(side_effects, list):
        raise ValueError("Tool side effects must be declared as a list.")

    allowed_scopes = tool.get("allowed_scopes")
    if not isinstance(allowed_scopes, list) or not allowed_scopes:
        raise ValueError("Tool allowed scopes must be declared as a non-empty list.")

    normalized = deepcopy(tool)
    normalized["name"] = name
    normalized["version"] = version
    normalized["description"] = description
    normalized["category"] = category
    normalized["risk_level"] = risk_level
    normalized["requires_approval"] = requires_approval
    normalized["supports_dry_run"] = supports_dry_run
    normalized["input_schema"] = deepcopy(input_schema)
    normalized["output_schema"] = deepcopy(output_schema)
    normalized["side_effects"] = list(side_effects)
    normalized["allowed_scopes"] = list(allowed_scopes)
    normalized["enabled"] = enabled
    return normalized


def _schema_required_keys(schema: Dict[str, Any]) -> List[str]:
    required = schema.get("required")
    if isinstance(required, list):
        return [str(item) for item in required]
    return []


def validate_arguments_against_schema(arguments: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    normalized_arguments = deepcopy(arguments or {})
    if not isinstance(normalized_arguments, dict):
        raise ValueError("Tool arguments must be a dictionary.")
    if not isinstance(schema, dict):
        raise ValueError("Tool input schema must be a dictionary.")

    if not schema:
        if normalized_arguments:
            raise ValueError("This tool does not accept arguments.")
        return normalized_arguments

    schema_type = str(schema.get("type") or "object")
    if schema_type != "object":
        raise ValueError("Only object tool input schemas are supported in Epoch VIII.")

    for key in _schema_required_keys(schema):
        if key not in normalized_arguments:
            raise ValueError(f"Missing required argument: {key}")

    properties = schema.get("properties")
    if isinstance(properties, dict) and schema.get("additionalProperties") is False:
        for key in normalized_arguments:
            if key not in properties:
                raise ValueError(f"Unexpected argument: {key}")

    return normalized_arguments


def validate_tool_request(request: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("Tool request must be a dictionary.")

    required_keys = [
        "request_id",
        "tool_name",
        "arguments",
        "requested_by",
        "session_id",
        "goal_id",
        "plan_id",
        "decision_id",
        "approval_id",
        "created_at",
        "status",
    ]
    missing = [key for key in required_keys if key not in request]
    if missing:
        raise ValueError(f"Tool request missing required keys: {', '.join(missing)}")

    request_id = str(request.get("request_id") or "").strip()
    tool_name = str(request.get("tool_name") or "").strip()
    requested_by = str(request.get("requested_by") or "").strip()
    session_id = str(request.get("session_id") or "").strip()
    created_at = str(request.get("created_at") or "").strip()
    status = str(request.get("status") or "").strip()

    if not request_id:
        raise ValueError("Tool request id is required.")
    if not tool_name:
        raise ValueError("Tool name is required on the request.")
    if not requested_by:
        raise ValueError("Tool request requester is required.")
    if not session_id:
        raise ValueError("Tool request session id is required.")
    if not created_at:
        raise ValueError("Tool request created_at is required.")
    if status not in VALID_TOOL_REQUEST_STATUSES:
        raise ValueError(f"Unsupported tool request status: {status}")

    arguments = request.get("arguments")
    if not isinstance(arguments, dict):
        raise ValueError("Tool request arguments must be a dictionary.")

    normalized = deepcopy(request)
    normalized["request_id"] = request_id
    normalized["tool_name"] = tool_name
    normalized["arguments"] = deepcopy(arguments)
    normalized["requested_by"] = requested_by
    normalized["session_id"] = session_id
    normalized["created_at"] = created_at
    normalized["status"] = status
    return normalized


def validate_tool_result(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Tool result must be a dictionary.")

    required_keys = [
        "request_id",
        "tool_name",
        "status",
        "success",
        "started_at",
        "completed_at",
        "duration_ms",
        "output",
        "error",
        "evidence_candidates",
        "side_effects_observed",
        "executor",
    ]
    missing = [key for key in required_keys if key not in result]
    if missing:
        raise ValueError(f"Tool result missing required keys: {', '.join(missing)}")

    status = str(result.get("status") or "").strip()
    if status not in VALID_TOOL_RESULT_STATUSES:
        raise ValueError(f"Unsupported tool result status: {status}")

    if not isinstance(result.get("success"), bool):
        raise ValueError("Tool result success must be a boolean.")
    if not isinstance(result.get("output"), dict):
        raise ValueError("Tool result output must be a dictionary.")
    if not isinstance(result.get("evidence_candidates"), list):
        raise ValueError("Tool result evidence candidates must be a list.")
    if not isinstance(result.get("side_effects_observed"), list):
        raise ValueError("Tool result observed side effects must be a list.")

    normalized = deepcopy(result)
    normalized["status"] = status
    return normalized
