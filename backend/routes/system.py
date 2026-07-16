from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.config import settings
from services.goal_engine import load_goal_store
from services.knowledge_graph import load_graph
from services.tool_approval import approve_request, create_approval_request, list_tool_requests, reject_request
from services.tool_contracts import build_tool_request
from services.tool_registry import get_tool, list_tools
from services.tool_results import load_tool_result_store

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/config")
def get_runtime_config():
    return {
        "chat_model": settings.chat_model,
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
        "tool_approval_ttl_seconds": settings.tool_approval_ttl_seconds,
    }


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
