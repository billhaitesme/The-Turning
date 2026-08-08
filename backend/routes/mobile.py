"""Authenticated Bridge Zero Mobile transport adapter.

The adapter projects existing runtime state. It does not own model selection,
rewrite responses, infer activity, or alter Model Lock.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from core.config import settings
from services.approval_engine import load_approval_store
from services.evidence_engine import load_evidence_store
from services.goal_engine import load_goal_store
from services.knowledge_graph import load_graph
from services.model_control import model_control
from services.plan_store import load_plan_store
from services.tool_request_store import load_tool_request_store
from services.tool_result_store import load_tool_result_store
from services.tool_approval import (
    approve_request,
    expire_approvals,
    list_tool_approvals,
    list_tool_requests as list_all_tool_requests,
    reject_request,
)


MOBILE_PREFIX = "/api/mobile/v1"
PROCESS_STARTED_AT = time.monotonic()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MobileMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    client_message_id: str = Field(min_length=1, max_length=128)


class MobileConversationRequest(BaseModel):
    title: Optional[str] = Field(default="Bridge Zero Mobile", max_length=200)


@dataclass
class RuntimeBindings:
    create_conversation: Callable[..., str]
    conversation_exists: Callable[[str], bool]
    get_full_messages: Callable[[str], list[dict[str, Any]]]
    get_conversation_meta: Callable[[str], Optional[dict[str, Any]]]
    get_db: Callable[[], Any]
    stream_chat: Callable[[str, str], Any]


_bindings: Optional[RuntimeBindings] = None


def configure_mobile_runtime(**bindings: Any) -> None:
    """Bind the adapter to the existing application runtime at startup."""
    global _bindings
    _bindings = RuntimeBindings(**bindings)


def _runtime() -> RuntimeBindings:
    if _bindings is None:
        raise HTTPException(status_code=503, detail="Mobile runtime adapter is unavailable.")
    return _bindings


def _configured_token() -> str:
    return os.getenv("MOBILE_AUTH_TOKEN", "").strip()


def require_mobile_auth(authorization: Optional[str] = Header(default=None)) -> None:
    expected = _configured_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile authentication is not configured.",
        )
    scheme, separator, candidate = (authorization or "").partition(" ")
    authenticated = (
        separator == " "
        and scheme.lower() == "bearer"
        and bool(candidate)
        and hmac.compare_digest(candidate, expected)
    )
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


router = APIRouter(
    prefix=MOBILE_PREFIX,
    tags=["bridge-zero-mobile"],
    dependencies=[Depends(require_mobile_auth)],
)


def load_mobile_chronicle() -> list[dict[str, Any]]:
    configured = os.getenv("CHRONICLE_PATH", "bridge/shared/mobile/chronicle.json")
    path = Path(configured)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return payload if isinstance(payload, list) else []


def _diagnostic(state: str, detail: Optional[str] = None) -> dict[str, Any]:
    return {"state": state, "detail": detail}


def _has_records(payload: Any, key: str) -> bool:
    return isinstance(payload, dict) and bool(payload.get(key))


@router.get("/compatibility")
def compatibility() -> dict[str, str]:
    return {
        "runtime_version": os.getenv("RUNTIME_VERSION", "0.4.1"),
        "required_mobile_version": os.getenv("REQUIRED_MOBILE_VERSION", "0.2.0"),
        "api_version": os.getenv("MOBILE_API_VERSION", "1"),
    }


@router.get("/status")
def runtime_status() -> dict[str, Any]:
    return build_runtime_status()


class MobileModelRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)


def _model_payload() -> dict[str, Any]:
    control = model_control.status()
    return {
        "current_model": control.get("active_model"),
        "available_models": control.get("available_models", []),
        "model_lock": bool(control.get("model_lock")),
    }


@router.get("/model")
def runtime_model() -> dict[str, Any]:
    return _model_payload()


@router.post("/model")
def set_runtime_model(request: MobileModelRequest) -> dict[str, Any]:
    # Explicit operator selection from the mobile console. Enforces the selectable
    # allowlist and records the change through Model Lock telemetry.
    try:
        model_control.set_selected_model(request.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _model_payload()


class ApprovalDecision(BaseModel):
    confirmed: bool = False


_PENDING_REQUEST_STATES = {"proposed", "awaiting_approval", "pending"}


def _pending_approvals() -> list[dict[str, Any]]:
    """Operator-facing view of runtime action requests awaiting approval.

    Enforces the short-lived approval window (expire_approvals) before surfacing,
    then joins each awaiting tool request to its still-pending approval challenge.
    """
    expire_approvals()
    approvals_by_request = {str(a.get("request_id") or ""): a for a in list_tool_approvals()}
    pending: list[dict[str, Any]] = []
    for request in list_all_tool_requests():
        if str(request.get("status") or "") not in _PENDING_REQUEST_STATES:
            continue
        approval = approvals_by_request.get(str(request.get("request_id") or ""))
        if not approval or str(approval.get("status") or "") != "pending":
            continue
        pending.append({
            "request_id": request.get("request_id"),
            "approval_id": approval.get("approval_id"),
            "tool_name": request.get("tool_name"),
            "arguments": request.get("arguments") or {},
            "requested_by": request.get("requested_by"),
            "created_at": approval.get("created_at"),
            "expires_at": approval.get("expires_at"),
            "status": approval.get("status"),
        })
    return pending


@router.get("/approvals")
def list_operator_approvals() -> dict[str, Any]:
    return {"approvals": _pending_approvals()}


@router.post("/approvals/{request_id}/approve")
def approve_operator_request(request_id: str, decision: ApprovalDecision) -> dict[str, Any]:
    # The operator confirms with a device biometric client-side; the runtime records
    # that an explicit, confirmed operator action authorized the request.
    if not decision.confirmed:
        raise HTTPException(status_code=400, detail="Operator biometric confirmation is required.")
    expire_approvals()
    try:
        approval = approve_request(request_id, approved_by="operator")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"approval": approval, "pending": _pending_approvals()}


@router.post("/approvals/{request_id}/deny")
def deny_operator_request(request_id: str) -> dict[str, Any]:
    try:
        approval = reject_request(request_id, rejected_by="operator")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"approval": approval, "pending": _pending_approvals()}


def build_runtime_status() -> dict[str, Any]:
    started = time.perf_counter()
    control = model_control.status()
    chronicle = load_mobile_chronicle()
    return {
        "online": True,
        "current_model": control.get("active_model"),
        "available_models": control.get("available_models", []),
        "model_lock": bool(control.get("model_lock")),
        "uptime_seconds": max(0, int(time.monotonic() - PROCESS_STARTED_AT)),
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "version": os.getenv("RUNTIME_VERSION", "0.4.1"),
        "chronicle_count": len(chronicle),
    }


@router.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    return build_mobile_diagnostics()


def build_mobile_diagnostics() -> dict[str, Any]:
    evidence = load_evidence_store()
    plans = load_plan_store()
    goals = load_goal_store()
    graph = load_graph()
    approvals = load_approval_store()
    requests = load_tool_request_store()
    results = load_tool_result_store()

    return {
        "identity": _diagnostic("healthy", "Core identity engine available"),
        "evidence": _diagnostic(
            "healthy" if _has_records(evidence, "facts") else "inactive",
            "Evidence store loaded",
        ),
        "planning": _diagnostic(
            "healthy" if _has_records(plans, "plans") or _has_records(goals, "goals") else "inactive",
            "Planning stores loaded",
        ),
        "deliberation": _diagnostic(
            "healthy" if _has_records(approvals, "approvals") else "inactive",
            "Approval store loaded",
        ),
        "tool_state": _diagnostic(
            "healthy" if settings.enable_tool_framework else "inactive",
            "Execution enabled" if settings.enable_tool_execution else "Execution disabled",
        ),
        "memory": _diagnostic("healthy", "Conversation database available"),
        "chronicle": _diagnostic(
            "healthy" if load_mobile_chronicle() else "inactive",
            "Chronicle loaded",
        ),
        "connection_health": _diagnostic("healthy", "Authenticated API request"),
        "counts": {
            "knowledge_nodes": len(graph.get("nodes", [])) if isinstance(graph, dict) else 0,
            "tool_requests": len(requests.get("requests", [])) if isinstance(requests, dict) else 0,
            "tool_results": len(results.get("results", [])) if isinstance(results, dict) else 0,
        },
    }


def _message_payload(message: dict[str, Any], index: int) -> dict[str, Any]:
    role_map = {"user": "operator", "assistant": "runtime", "system": "system"}
    created_at = message.get("created_at") or datetime.now(timezone.utc).isoformat()
    return {
        "id": str(message.get("id") or f"message-{index}"),
        "role": role_map.get(str(message.get("role", "system")), "system"),
        "content": str(message.get("content") or ""),
        "created_at": created_at,
    }


def latest_conversation_id() -> Optional[str]:
    runtime = _runtime()
    conn = runtime.get_db()
    try:
        row = conn.execute(
            "SELECT id FROM conversations ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        return str(row["id"]) if row else None
    finally:
        conn.close()


def _conversation_payload(conversation_id: str) -> dict[str, Any]:
    runtime = _runtime()
    if not runtime.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    messages = runtime.get_full_messages(conversation_id)
    return {
        "id": conversation_id,
        "messages": [_message_payload(message, index) for index, message in enumerate(messages)],
    }


@router.post("/conversations")
def create_mobile_conversation(request: MobileConversationRequest) -> dict[str, Any]:
    conversation_id = _runtime().create_conversation(title=request.title)
    return _conversation_payload(conversation_id)


@router.get("/conversations/active")
def active_conversation() -> dict[str, Any]:
    conversation_id = latest_conversation_id()
    if conversation_id is None:
        raise HTTPException(status_code=404, detail="No active conversation.")
    return _conversation_payload(conversation_id)


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str) -> dict[str, Any]:
    return _conversation_payload(conversation_id)


@router.post("/conversations/{conversation_id}/messages")
def stream_mobile_message(conversation_id: str, request: MobileMessageRequest):
    runtime = _runtime()
    if not runtime.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    # client_message_id provides retry identity for future idempotency support.
    # The established /chat/stream path remains the sole response authority.
    return runtime.stream_chat(request.content, conversation_id)


@router.get("/chronicle")
def chronicle() -> list[dict[str, Any]]:
    return load_mobile_chronicle()
