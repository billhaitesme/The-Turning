from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.config import settings
from services.goal_engine import load_goal_store
from services.knowledge_graph import load_graph
from services.model_control import model_control
from services.evidence_engine import (
    extract_durable_evidence_store,
    extract_session_scoped_evidence_store,
    load_evidence_store,
    load_session_evidence_store,
    merge_evidence_stores,
    save_evidence_store,
    save_session_evidence_store,
)
from services import (agent_loop, command_console, command_registry, deep_seat, host_clock,
                      network_breaker, toolwright)
from services.tool_approval import approve_request, create_approval_request, load_tool_approval_store, reject_request
from services.tool_contracts import build_tool_request
from services.tool_evidence_bridge import execute_backend_health_check_request
from services.tool_registry import get_tool, list_tools
from services.tool_request_store import get_tool_request, list_tool_requests, load_tool_request_store, upsert_tool_request
from services.tool_result_store import load_tool_result_store
from services.adapters.backend_health_check import BackendHealthCheckAdapter

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def get_system_status(request: Request) -> Dict[str, Any]:
    return {
        "status": "ok",
        # The app's own version string — the versioning authority's backend source, never a
        # second hardcode here.
        "version": getattr(request.app, "version", None),
        "agent_loop_enabled": agent_loop.agent_loop_enabled(),
        "network_breaker_on": network_breaker.breaker_is_on(),
        "model_control": model_control.status(),
        "tool_framework": _tool_framework_payload(),
        # the consoles format every time 24-hour in the HOST's zone, not the browser's
        "host_clock": host_clock.host_clock(),
    }


# ----------------------------------------------------------------------- XIII-B: the breaker
class BreakerRequest(BaseModel):
    on: bool
    changed_by: str = Field(default="operator", max_length=120)


@router.get("/breaker")
def get_network_breaker() -> Dict[str, Any]:
    state = network_breaker.breaker_state()
    state["history"] = (state.get("history") or [])[-20:][::-1]
    return state


@router.post("/breaker")
def set_network_breaker(req: BreakerRequest) -> Dict[str, Any]:
    """Flip the standing network breaker — an explicit recorded operator action (ADR 0026).
    The model has no path to this route: no registry command maps to it, by design."""
    state = network_breaker.set_breaker(req.on, changed_by=f"operator:{req.changed_by}",
                                        channel="desktop")
    state["history"] = (state.get("history") or [])[-20:][::-1]
    return state


# ----------------------------------------------------------------------- the deep rung's seat
class DeepSeatRequest(BaseModel):
    model: str = Field(max_length=200)
    changed_by: str = Field(default="operator", max_length=120)


@router.get("/deep-seat")
def get_deep_seat() -> Dict[str, Any]:
    data = deep_seat.state()
    data["history"] = (data.get("history") or [])[-10:][::-1]
    return data


@router.post("/deep-seat")
def set_deep_seat(req: DeepSeatRequest) -> Dict[str, Any]:
    """Which model is the LOCAL deep rung — a recorded operator action from a console. No
    registry command maps here: the model chooses local vs frontier, never which local model."""
    try:
        data = deep_seat.set_local_model(req.model, changed_by=f"operator:{req.changed_by}",
                                         channel="desktop")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    data["history"] = (data.get("history") or [])[-10:][::-1]
    return data


@router.get("/fetch-log")
def get_fetch_log(limit: int = 50) -> Dict[str, Any]:
    return {"entries": network_breaker.list_fetch_log(limit=limit),
            "breaker_on": network_breaker.breaker_is_on()}


# ----------------------------------------------------------------------- faces: the gallery
# Enrollment is an operator console action (biometric data, local only, never committed, never
# on any non-local seat). The seat reads identities through recognize_faces; it cannot enroll.
class EnrollFaceBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    image: str = Field(..., min_length=16)  # data URL or bare base64 of one clear photo


@router.get("/faces")
def get_faces() -> Dict[str, Any]:
    from services import face_engine
    return {"people": face_engine.list_people(),
            "match_threshold": face_engine.MATCH_THRESHOLD,
            "engine_ready": (face_engine.MODEL_DIR / face_engine.DET_MODEL).exists()
                            and (face_engine.MODEL_DIR / face_engine.REC_MODEL).exists()}


@router.post("/faces/enroll")
def enroll_face(body: EnrollFaceBody) -> Dict[str, Any]:
    import base64 as _b64
    import re as _re

    from services import face_engine
    raw = _re.sub(r"^data:image/\w+;base64,", "", body.image, flags=_re.IGNORECASE)
    try:
        blob = _b64.b64decode(raw, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Enrollment image is not valid base64.") from exc
    try:
        entry = face_engine.enroll(body.name, blob)
    except face_engine.FaceEngineUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"person": entry}


@router.delete("/faces/{person_id}")
def delete_face(person_id: str) -> Dict[str, Any]:
    from services import face_engine
    if not face_engine.remove_person(person_id):
        raise HTTPException(status_code=404, detail=f"No enrolled person {person_id}.")
    return {"removed": person_id}


# ----------------------------------------------------------------------- XIII-D: the Toolwright
class CapabilityRequestBody(BaseModel):
    need: str = Field(..., min_length=1, max_length=300)
    why: str = Field(default="", max_length=500)


@router.get("/toolwright")
def get_toolwright() -> Dict[str, Any]:
    return {"requests": toolwright.list_requests()}


@router.post("/toolwright/requests")
def file_capability_request(body: CapabilityRequestBody) -> Dict[str, Any]:
    entry = toolwright.file_request(body.need, body.why,
                                    requested_by="operator:desktop", session_id="toolwright-desktop")
    return {"request": entry}


@router.post("/toolwright/requests/{request_id}/prepare")
def prepare_capability_request(request_id: str) -> Dict[str, Any]:
    """Find → quarantine → verify, one operator press. Verification's fixture call needs the
    network breaker ON (it is a logged egress like any other)."""
    try:
        if toolwright.is_authored(toolwright.get_request(request_id)):
            toolwright.reprepare_authored(request_id)  # ADR 0027: its candidate is its own
        else:
            toolwright.find_candidate(request_id)
        toolwright.quarantine_candidate(request_id)
        entry = toolwright.verify_candidate(request_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"request": entry}


@router.post("/toolwright/requests/{request_id}/induct")
def induct_capability_request(request_id: str) -> Dict[str, Any]:
    """First press raises the biometric approval; after the operator confirms on a mobile
    console, the next press completes the induction. Every press is answered honestly."""
    try:
        entry = toolwright.get_request(request_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Unknown capability request {request_id}.")
        if entry["status"] == "verified" or toolwright.induction_approval_is_dead(entry):
            entry = toolwright.request_induction(request_id, requested_by="operator:desktop")
            return {"request": entry,
                    "note": "Approval raised — confirm with the biometric on a mobile console, "
                            "then press induct again to complete."}
        entry = toolwright.complete_induction(request_id)
        return {"request": entry, "note": f"Inducted: '{entry['candidate']['name']}' is live."}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/toolwright/requests/{request_id}/deny")
def deny_capability_request(request_id: str) -> Dict[str, Any]:
    try:
        entry = toolwright.deny_request(request_id, denied_by="operator:desktop")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"request": entry}


# ----------------------------------------------------------------------- XIII-A: desktop commands
# The web console renders the registry it is given, it never defines it (ADR 0015). Initiations
# from here carry channel "desktop": direct commands execute, approval commands enter the IX-C
# pipeline and still require the mobile biometric (the desktop cannot self-approve).
class CommandInitiateBody(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)


@router.get("/commands")
def get_system_commands() -> Dict[str, Any]:
    return {
        "commands": command_registry.list_commands(),
        "execution_enabled": command_console.command_execution_enabled(),
    }


@router.get("/commands/history")
def get_system_command_history(limit: int = 50) -> Dict[str, Any]:
    return {"history": command_console.list_command_history(limit=max(1, min(200, limit)))}


@router.post("/commands/{name}")
def initiate_system_command(name: str, body: Optional[CommandInitiateBody] = None) -> Dict[str, Any]:
    try:
        entry = command_console.initiate_command(
            name,
            requested_by="operator:desktop",
            channel="desktop",
            arguments=(body.arguments if body else {}) or {},
        )
    except command_console.CommandError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    return {"command": entry}

@router.get("/config")
def get_runtime_config():
    import os as _os
    return {
        "chat_model": model_control.select_chat_model(),
        "active_chat_model": model_control.select_chat_model(),
        "direct_chat_model": _os.getenv("DIRECT_CHAT_MODEL", "huihui_ai/gemma-4-abliterated:12b"),
        "selectable_chat_models": list(settings.selectable_chat_models),
        "model_lock": settings.model_lock,
        "allow_topic_routing": settings.allow_topic_routing,
        "allow_secondary_rewrite": settings.allow_secondary_rewrite,
        "allow_automatic_model_fallback": settings.allow_automatic_model_fallback,
        "reasoning_model": settings.reasoning_model,
        "vision_model": settings.vision_model,
        "router_model": settings.router_model,
        "embedding_model": settings.embedding_model,
        "network_mode": settings.network_mode,
        "personality_mode": settings.personality_mode,
        "enable_tool_framework": settings.enable_tool_framework,
        "enable_tool_execution": settings.enable_tool_execution,
        "enable_tool_dry_run": settings.enable_tool_dry_run,
        "enable_critical_tools": settings.enable_critical_tools,
        "enable_backend_health_check": settings.enable_backend_health_check,
        "backend_health_check_timeout_seconds": settings.backend_health_check_timeout_seconds,
        "backend_health_check_paths": settings.backend_health_check_paths,
        "tool_approval_ttl_seconds": settings.tool_approval_ttl_seconds,
    }


class ActiveModelRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=200)


@router.get("/model-control")
def get_model_control() -> Dict[str, Any]:
    payload = model_control.status()
    payload["telemetry"] = model_control.telemetry()
    return payload


@router.post("/model-control")
def set_model_control(req: ActiveModelRequest) -> Dict[str, Any]:
    # set_selected_model enforces the selectable allowlist and records the change
    # through Model Lock telemetry as an explicit operator selection.
    try:
        model_control.set_selected_model(req.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return model_control.status()


@router.get("/cognition")
def get_cognition_state():
    return {
        "goals": load_goal_store(),
        "knowledge_graph": load_graph(),
    }


class ToolRequestCreateRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "user"
    session_id: str
    goal_id: Optional[str] = None
    plan_id: Optional[str] = None
    decision_id: Optional[str] = None
    approval_id: Optional[str] = None


class ToolApprovalActorRequest(BaseModel):
    approved_by: Optional[str] = "user"


class BackendHealthExecuteRequest(BaseModel):
    request_id: str


def _tool_framework_payload() -> Dict[str, Any]:
    return {
        "enabled": settings.enable_tool_framework,
        "execution_enabled": settings.enable_tool_execution,
        "dry_run_enabled": settings.enable_tool_dry_run,
        "critical_tools_enabled": settings.enable_critical_tools,
        "approval_ttl_seconds": settings.tool_approval_ttl_seconds,
    }


@router.get("/tools")
def get_tools() -> Dict[str, Any]:
    payload = _tool_framework_payload()
    payload["tools"] = list_tools() if settings.enable_tool_framework else []
    return payload


@router.get("/tools/{tool_name}")
def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    entry = get_tool(tool_name)
    if not entry:
        raise HTTPException(status_code=404, detail="Tool not found.")
    payload = _tool_framework_payload()
    payload["tool"] = entry.get("descriptor")
    return payload


@router.get("/tool-requests")
def get_tool_requests() -> Dict[str, Any]:
    payload = _tool_framework_payload()
    payload["requests"] = list_tool_requests() if settings.enable_tool_framework else []
    return payload


@router.get("/tool-results")
def get_tool_results() -> Dict[str, Any]:
    payload = _tool_framework_payload()
    store = load_tool_result_store()
    payload["results"] = store.get("results", []) if isinstance(store, dict) else []
    return payload


def _load_scoped_evidence_store(session_id: str) -> Dict[str, Any]:
    durable_store = load_evidence_store()
    session_store = load_session_evidence_store(session_id=session_id)
    return merge_evidence_stores(durable_store, session_store)


def _persist_scoped_evidence_store(session_id: str, evidence_store: Dict[str, Any]) -> None:
    durable_store = extract_durable_evidence_store(evidence_store)
    session_store = extract_session_scoped_evidence_store(evidence_store)
    save_evidence_store(durable_store)
    save_session_evidence_store(session_id=session_id, store=session_store)


@router.post("/tool-requests")
def create_tool_request(req: ToolRequestCreateRequest) -> Dict[str, Any]:
    if not settings.enable_tool_framework:
        raise HTTPException(status_code=503, detail="Tool framework is disabled.")
    request = build_tool_request(
        tool_name=req.tool_name,
        arguments=req.arguments,
        requested_by=req.requested_by,
        session_id=req.session_id,
        goal_id=req.goal_id,
        plan_id=req.plan_id,
        decision_id=req.decision_id,
        approval_id=req.approval_id,
    )
    approval = create_approval_request(request)
    request["approval_id"] = approval["approval_id"]
    request["status"] = "awaiting_approval"
    return {"request": request, "approval": approval}


@router.post("/tool-requests/{request_id}/approve")
def approve_tool_request(request_id: str, req: ToolApprovalActorRequest) -> Dict[str, Any]:
    if not settings.enable_tool_framework:
        raise HTTPException(status_code=503, detail="Tool framework is disabled.")
    return {"approval": approve_request(request_id, approved_by=req.approved_by)}


@router.post("/tool-requests/{request_id}/reject")
def reject_tool_request(request_id: str, req: ToolApprovalActorRequest) -> Dict[str, Any]:
    if not settings.enable_tool_framework:
        raise HTTPException(status_code=503, detail="Tool framework is disabled.")
    return {"approval": reject_request(request_id, rejected_by=req.approved_by)}


@router.post("/tool-requests/{request_id}/execute")
def execute_tool_request(request_id: str, req: BackendHealthExecuteRequest) -> Dict[str, Any]:
    if not settings.enable_tool_framework or not settings.enable_tool_execution or not settings.enable_backend_health_check:
        raise HTTPException(status_code=503, detail="Tool execution is disabled.")
    if request_id != req.request_id:
        raise HTTPException(status_code=400, detail="Request id mismatch.")

    request_store = load_tool_request_store()
    request_record = get_tool_request(request_id, request_store)
    if request_record is None:
        raise HTTPException(status_code=404, detail="Tool request not found.")
    if str(request_record.get("tool_name") or "") != "backend_health_check":
        raise HTTPException(status_code=400, detail="Only backend_health_check can be executed here.")

    evidence_store = _load_scoped_evidence_store(str(request_record.get("session_id") or ""))
    approval_store = load_tool_approval_store()
    result_store = load_tool_result_store()
    adapter = BackendHealthCheckAdapter()

    outcome = execute_backend_health_check_request(
        request_record=request_record,
        adapter=adapter,
        evidence_store=evidence_store,
        approval_store=approval_store,
        request_store=request_store,
        result_store=result_store,
        previous_evidence_store=evidence_store,
    )
    _persist_scoped_evidence_store(str(request_record.get("session_id") or ""), outcome["evidence_store"])
    return outcome


# ----------------------------------------------------------------------------- IX-D commands (desktop)
class SystemCommandInitiateRequest(BaseModel):
    arguments: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


@router.get("/commands")
def list_system_commands() -> Dict[str, Any]:
    """Command registry for the desktop console. Desktop may initiate; approval-gated commands
    still complete only on a mobile biometric (ADR 0015 — desktop cannot self-approve)."""
    return {"commands": command_registry.list_commands(),
            "execution_enabled": command_console.command_execution_enabled()}


@router.post("/commands/{name}")
def initiate_system_command(name: str, req: Optional[SystemCommandInitiateRequest] = None) -> Dict[str, Any]:
    if not settings.enable_tool_framework:
        raise HTTPException(status_code=503, detail="Tool framework is disabled.")
    req = req or SystemCommandInitiateRequest()
    try:
        entry = command_console.initiate_command(name, requested_by="operator", channel="desktop",
                                                 session_id=req.session_id, arguments=req.arguments)
    except command_console.CommandError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    return {"command": entry}


@router.get("/commands/history")
def system_command_history(limit: int = 50) -> Dict[str, Any]:
    return {"history": command_console.list_command_history(limit=limit)}
