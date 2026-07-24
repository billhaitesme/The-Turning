from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, Optional

from services.tool_approval import consume_approval, validate_approval_for_request
from services.tool_contracts import (
    utc_now_iso,
    validate_arguments_against_schema,
    validate_tool_request,
)
from services.tool_registry import get_tool
from services.tool_evidence_bridge import tool_result_to_evidence_candidates
from services.tool_results import create_tool_result, record_tool_result


def _scope_is_valid(descriptor: Dict[str, Any], request: Dict[str, Any], arguments: Dict[str, Any]) -> bool:
    allowed_scopes = [str(item).lower() for item in descriptor.get("allowed_scopes") or []]
    if not allowed_scopes:
        return False
    if "localhost" in allowed_scopes:
        return True

    candidate_values = []
    for key in ("scope", "target", "url", "endpoint", "path"):
        value = arguments.get(key)
        if isinstance(value, str):
            candidate_values.append(value.lower())
    for key in ("session_id", "goal_id", "plan_id", "decision_id"):
        value = request.get(key)
        if isinstance(value, str):
            candidate_values.append(value.lower())
    return any(value in allowed_scopes for value in candidate_values)


def _failure_result(
    *,
    request: Dict[str, Any],
    status: str,
    code: str,
    message: str,
    started_at: str,
    completed_at: str,
    execution_mode: str,
    side_effects_observed: Optional[list] = None,
) -> Dict[str, Any]:
    result = create_tool_result(
        request_id=str(request.get("request_id") or ""),
        tool_name=str(request.get("tool_name") or ""),
        status=status,
        success=False,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0.0, (datetime.fromisoformat(completed_at.replace("Z", "+00:00")) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds() * 1000.0),
        output={},
        error={"code": code, "message": message},
        evidence_candidates=[],
        side_effects_observed=side_effects_observed or [],
        executor="local_adapter",
        execution_mode=execution_mode,
    )
    record_tool_result(result)
    return result


def execute_tool_request(
    *,
    request: Dict[str, Any],
    registry,
    approval_store,
    dry_run: bool = False,
) -> Dict[str, Any]:
    started_at = utc_now_iso()
    started_perf = perf_counter()
    completed_at = started_at

    try:
        validated_request = validate_tool_request(request)
    except Exception as exc:
        return _failure_result(
            request=request if isinstance(request, dict) else {},
            status="failed",
            code="invalid_request",
            message=str(exc),
            started_at=started_at,
            completed_at=utc_now_iso(),
            execution_mode="dry_run" if dry_run else "live",
        )

    tool_entry = None
    if hasattr(registry, "get_tool"):
        tool_entry = registry.get_tool(validated_request["tool_name"])
    elif isinstance(registry, dict):
        tool_entry = registry.get(validated_request["tool_name"])

    if not tool_entry:
        return _failure_result(
            request=validated_request,
            status="failed",
            code="tool_missing",
            message=f"Tool not registered: {validated_request['tool_name']}",
            started_at=started_at,
            completed_at=utc_now_iso(),
            execution_mode="dry_run" if dry_run else "live",
        )

    descriptor = tool_entry.get("descriptor") or {}
    adapter = tool_entry.get("adapter")
    if not descriptor.get("enabled", False):
        return _failure_result(
            request=validated_request,
            status="failed",
            code="tool_disabled",
            message=f"Tool is disabled: {validated_request['tool_name']}",
            started_at=started_at,
            completed_at=utc_now_iso(),
            execution_mode="dry_run" if dry_run else "live",
        )

    if str(descriptor.get("risk_level") or "") == "critical":
        return _failure_result(
            request=validated_request,
            status="failed",
            code="risk_unsupported",
            message="Critical tools are unsupported by the bounded execution policy.",
            started_at=started_at,
            completed_at=utc_now_iso(),
            execution_mode="dry_run" if dry_run else "live",
        )

    if not _scope_is_valid(descriptor, validated_request, validated_request.get("arguments") or {}):
        return _failure_result(
            request=validated_request,
            status="failed",
            code="scope_invalid",
            message="Tool request is outside the allowed scope.",
            started_at=started_at,
            completed_at=utc_now_iso(),
            execution_mode="dry_run" if dry_run else "live",
        )

    try:
        arguments = validate_arguments_against_schema(validated_request.get("arguments") or {}, descriptor.get("input_schema") or {})
        if adapter is None:
            raise ValueError("No adapter is registered for this tool.")
        validated_arguments = adapter.validate_arguments(arguments)
    except Exception as exc:
        return _failure_result(
            request=validated_request,
            status="failed",
            code="invalid_arguments",
            message=str(exc),
            started_at=started_at,
            completed_at=utc_now_iso(),
            execution_mode="dry_run" if dry_run else "live",
        )

    if not dry_run and descriptor.get("requires_approval", False):
        try:
            validate_approval_for_request({**validated_request, "arguments": validated_arguments}, approval_store=approval_store)
        except Exception as exc:
            return _failure_result(
                request=validated_request,
                status="failed",
                code="approval_required" if "does not exist" in str(exc).lower() else "approval_invalid",
                message=str(exc),
                started_at=started_at,
                completed_at=utc_now_iso(),
                execution_mode="live",
            )

    request["status"] = "executing"
    if dry_run:
        try:
            output = adapter.dry_run(validated_arguments)
        except Exception as exc:
            return _failure_result(
                request=validated_request,
                status="failed",
                code="adapter_exception",
                message=str(exc),
                started_at=started_at,
                completed_at=utc_now_iso(),
                execution_mode="dry_run",
            )

        completed_at = utc_now_iso()
        result = create_tool_result(
            request_id=validated_request["request_id"],
            tool_name=validated_request["tool_name"],
            status="completed",
            success=True,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=max(0.0, (datetime.fromisoformat(completed_at.replace("Z", "+00:00")) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds() * 1000.0),
            output=deepcopy(output or {}),
            error=None,
            evidence_candidates=[],
            side_effects_observed=[],
            executor="local_adapter",
            execution_mode="dry_run",
        )
        record_tool_result(result)
        request["status"] = "completed"
        return result

    attempted_execution = False
    approval_to_consume = None
    if descriptor.get("requires_approval", False):
        approval_to_consume = validate_approval_for_request({**validated_request, "arguments": validated_arguments}, approval_store=approval_store)

    try:
        attempted_execution = True
        output = adapter.execute(validated_arguments)
        success = bool(output.get("success", True)) if isinstance(output, dict) else True
        raw_output = deepcopy(output.get("output") if isinstance(output, dict) and "output" in output else output or {})
        side_effects_observed = deepcopy(output.get("side_effects_observed") if isinstance(output, dict) else []) or []
        if validated_request["tool_name"] == "backend_health_check":
            status = "completed"
            error = None
        elif success:
            status = "completed"
            error = None
        else:
            status = "failed"
            error = {"code": str(output.get("status") or "tool_failed"), "message": str(raw_output.get("message") or "Tool execution reported failure.")}
        completed_at = utc_now_iso()
        result = create_tool_result(
            request_id=validated_request["request_id"],
            tool_name=validated_request["tool_name"],
            status=status,
            success=success,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=max(0.0, (datetime.fromisoformat(completed_at.replace("Z", "+00:00")) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds() * 1000.0),
            output=raw_output,
            error=error,
            evidence_candidates=[],
            side_effects_observed=side_effects_observed,
            executor="local_adapter",
            execution_mode="live",
        )
    except Exception as exc:
        completed_at = utc_now_iso()
        result = create_tool_result(
            request_id=validated_request["request_id"],
            tool_name=validated_request["tool_name"],
            status="failed",
            success=False,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=max(0.0, (datetime.fromisoformat(completed_at.replace("Z", "+00:00")) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds() * 1000.0),
            output={},
            error={"code": "adapter_exception", "message": str(exc)},
            evidence_candidates=[],
            side_effects_observed=[],
            executor="local_adapter",
            execution_mode="live",
        )
    finally:
        if attempted_execution and approval_to_consume is not None:
            try:
                consume_approval(approval_to_consume["approval_id"], approval_store=approval_store)
            except Exception:
                pass

    request["status"] = result["status"]
    result["evidence_candidates"] = tool_result_to_evidence_candidates(result)
    record_tool_result(result)
    return result
