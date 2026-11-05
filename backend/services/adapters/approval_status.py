"""approval_status — a read-only bounded tool that reports the IX-C approval pipeline's truth.

XIII-A follow-up (operator-observed 2026-11-05): after raising a gated command, the chat seat had
no way to *check* whether the operator's biometric had landed — so it either parroted its last
sentence or, worse, fabricated "your confirmation has been received." This read closes that gap:
"did my approval go through?" now has a verifiable answer. No side effects — it reads the stores
and returns; its command is low/direct (nothing to gate on a read).
"""
from __future__ import annotations

from typing import Any, Dict, List

from services.tool_approval import list_tool_approvals
from services.tool_contracts import validate_tool_definition
from services.tool_request_store import list_tool_requests


class ApprovalStatusAdapter:
    def describe(self) -> Dict[str, Any]:
        return {"name": "approval_status", "version": 1,
                "description": "Reads the current state of tool requests and operator approvals."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if arguments and set(arguments):
            raise ValueError("approval_status takes no arguments.")
        return {}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        return {"would_read": ["tool_requests", "tool_approvals"], "safe": True, "side_effects": []}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        approvals = {a.get("request_id"): a for a in list_tool_approvals()}
        requests = list_tool_requests()
        recent: List[Dict[str, Any]] = []
        for request in sorted(requests, key=lambda r: str(r.get("created_at") or ""), reverse=True)[:8]:
            approval = approvals.get(request.get("request_id")) or {}
            recent.append({
                "tool_name": request.get("tool_name"),
                "request_status": request.get("status"),
                "approval_status": approval.get("status"),
                "biometric_confirmed": approval.get("confirmation") == "biometric",
                "requested_by": request.get("requested_by"),
                "created_at": request.get("created_at"),
                "expires_at": approval.get("expires_at"),
            })
        pending = [r for r in recent if r["request_status"] == "awaiting_approval"]
        return {
            "pending_count": len(pending),
            "pending": pending,
            "recent": recent,
            "note": "request_status 'completed' means the gated tool actually executed; "
                    "'awaiting_approval' means the operator has NOT confirmed yet.",
        }


APPROVAL_STATUS_DESCRIPTOR = validate_tool_definition(
    {
        "name": "approval_status",
        "version": 1,
        "description": "Reads the IX-C pipeline: pending tool requests and whether operator "
                       "approvals (biometric) have landed. Read-only.",
        "category": "diagnostic",
        "risk_level": "low",
        "requires_approval": False,
        "supports_dry_run": True,
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)
