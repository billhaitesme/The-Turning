from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from services.evidence_engine import invalidate_dependents, normalize_evidence_record, set_evidence
from services.goal_engine import load_goal_store
from services.reasoning_pipeline import run_reasoning_pipeline
from services.tool_approval import consume_approval, validate_approval_for_request
from services.tool_contracts import utc_now_iso, validate_tool_request
from services.tool_result_store import append_tool_result, save_tool_result_store
from services.tool_request_store import save_tool_request_store, update_request_status
from services.tool_approval import save_tool_approval_store
from services.tool_results import create_tool_result


def _configured_backend_port(evidence_store: Dict[str, Any]) -> Optional[int]:
    facts = evidence_store.get("facts", {}) if isinstance(evidence_store, dict) else {}
    backend_port = normalize_evidence_record(facts.get("backend_port")).get("value") if isinstance(facts, dict) else None
    try:
        return int(backend_port) if backend_port is not None else None
    except Exception:
        return None


def _checked_port_from_url(url: str) -> Optional[int]:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(str(url or ""))
        return int(parsed.port) if parsed.port is not None else None
    except Exception:
        return None


def _result_is_trusted_backend_health_check(result: Dict[str, Any]) -> bool:
    return (
        isinstance(result, dict)
        and str(result.get("tool_name") or "") == "backend_health_check"
        and str(result.get("execution_mode") or "live") == "live"
        and str(result.get("executor") or "") == "local_adapter"
        and str(result.get("status") or "") == "completed"
    )


def tool_result_to_evidence_candidates(result: dict) -> list[dict]:
    if not _result_is_trusted_backend_health_check(result):
        return []

    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    checked_url = str(output.get("checked_url") or "").strip()
    if not checked_url:
        return []

    success = bool(result.get("success"))
    value = "online" if success else "offline"
    candidate = {
        "key": "backend_health",
        "value": value,
        "state_type": "verified",
        "source": "health_check",
        "confidence": 1.0,
        "observed_at": output.get("checked_at") or result.get("completed_at"),
        "scope": "runtime",
        "dependencies": ["backend_port"],
        "metadata": {
            "request_id": result.get("request_id"),
            "tool_name": result.get("tool_name"),
            "checked_url": checked_url,
            "status_code": output.get("status_code"),
            "latency_ms": output.get("latency_ms"),
        },
    }
    if not success:
        candidate["metadata"]["error"] = output.get("error") or result.get("error", {}).get("message")
    return [candidate]


def apply_tool_result_to_evidence_store(
    evidence_store: Dict[str, Any],
    result: Dict[str, Any],
    *,
    configured_backend_port: Optional[int] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    updated_store = deepcopy(evidence_store) if isinstance(evidence_store, dict) else {"version": 1, "facts": {}}
    updated_store.setdefault("version", 1)
    updated_store.setdefault("facts", {})

    if not _result_is_trusted_backend_health_check(result):
        return updated_store, []

    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    checked_url = str(output.get("checked_url") or "").strip()
    checked_port = _checked_port_from_url(checked_url)

    if configured_backend_port is not None and checked_port is not None and int(configured_backend_port) != int(checked_port):
        updated_store = set_evidence(
            updated_store,
            key="backend_health",
            record={
                "key": "backend_health",
                "value": None,
                "state_type": "unknown",
                "source": "health_check",
                "confidence": 1.0,
                "observed_at": output.get("checked_at") or result.get("completed_at"),
                "dependencies": ["backend_port"],
                "scope": "runtime",
                "notes": "endpoint mismatch",
            },
        )
        return invalidate_dependents(updated_store, "backend_port"), []

    candidates = tool_result_to_evidence_candidates(result)
    for candidate in candidates:
        updated_store = set_evidence(updated_store, key=candidate["key"], record={
            "key": candidate["key"],
            "value": candidate["value"],
            "state_type": candidate["state_type"],
            "source": candidate["source"],
            "confidence": candidate["confidence"],
            "observed_at": candidate["observed_at"],
            "dependencies": candidate["dependencies"],
            "scope": candidate["scope"],
            "notes": "Trusted health-check adapter result.",
            "checked_url": candidate["metadata"].get("checked_url"),
            "checked_at": candidate["observed_at"],
        })
    return updated_store, candidates


def execute_backend_health_check_request(
    *,
    request_record: Dict[str, Any],
    adapter,
    evidence_store: Dict[str, Any],
    approval_store: Dict[str, Any],
    request_store: Dict[str, Any],
    result_store: Dict[str, Any],
    previous_evidence_store: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    validated_request = validate_tool_request(request_record)
    validated_arguments = adapter.validate_arguments(validated_request.get("arguments") or {})
    validate_approval_for_request({**validated_request, "arguments": validated_arguments}, approval_store=approval_store)

    result_payload: Dict[str, Any]
    execution_mode = "live"
    adapter_failure: Optional[str] = None
    try:
        result_payload = adapter.execute(validated_arguments)
    except Exception as exc:  # noqa: BLE001
        adapter_failure = str(exc)
        now = utc_now_iso()
        result_payload = {
            "target": "backend",
            "checked_url": f"http://127.0.0.1:{validated_arguments['port']}/health",
            "success": False,
            "status_code": None,
            "latency_ms": 3000.0,
            "checked_at": now,
            "error": str(exc),
        }
        execution_mode = "live"

    result_status = "failed" if adapter_failure else "completed"
    result_success = bool(result_payload.get("success", False))
    configured_port = _configured_backend_port(evidence_store)
    checked_url = str(result_payload.get("checked_url") or "")
    checked_port = _checked_port_from_url(checked_url)

    if adapter_failure is None and configured_port is not None and checked_port is not None and int(configured_port) != int(checked_port):
        result_status = "endpoint_mismatch"
        result_success = False
        result_payload = {**result_payload, "error": "endpoint mismatch"}

    started_at = result_payload.get("checked_at") or result_payload.get("started_at") or utc_now_iso()
    completed_at = result_payload.get("checked_at") or result_payload.get("completed_at") or started_at
    tool_result = create_tool_result(
        request_id=validated_request["request_id"],
        tool_name=validated_request["tool_name"],
        status=result_status,
        success=result_success,
        started_at=started_at or result_payload.get("checked_at") or "1970-01-01T00:00:00+00:00",
        completed_at=completed_at or result_payload.get("checked_at") or "1970-01-01T00:00:00+00:00",
        duration_ms=float(result_payload.get("latency_ms") or 0.0),
        output=deepcopy(result_payload),
        error=None if result_status in {"completed", "endpoint_mismatch"} else {"code": "adapter_exception", "message": adapter_failure or str(result_payload.get("error") or "adapter error")},
        evidence_candidates=[],
        side_effects_observed=[],
        executor="local_adapter",
        execution_mode=execution_mode,
    )
    append_tool_result(tool_result, store=result_store)
    save_tool_result_store(result_store)

    update_request_status(
        validated_request["request_id"],
        result_status,
        store=request_store,
        extra_fields={"approval_id": validated_request.get("approval_id"), "updated_at": completed_at},
    )
    save_tool_request_store(request_store)

    try:
        consume_approval(validated_request.get("approval_id") or "", approval_store=approval_store, request_store=request_store)
    except Exception:
        pass
    save_tool_approval_store(approval_store)

    updated_evidence_store, candidates = apply_tool_result_to_evidence_store(
        evidence_store,
        tool_result,
        configured_backend_port=configured_port,
    )

    reasoning_result = run_reasoning_pipeline(
        evidence_store=updated_evidence_store,
        goal_store=load_goal_store(),
        previous_evidence_store=previous_evidence_store,
    )

    return {
        "request": validated_request,
        "result": tool_result,
        "evidence_store": updated_evidence_store,
        "candidates": candidates,
        "reasoning_result": reasoning_result,
    }
