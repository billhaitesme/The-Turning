from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List


VALID_DECISION_STATUSES = {"proposed", "active", "superseded", "withdrawn"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_decision(decision: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []

    if not isinstance(decision, dict):
        return {"valid": False, "errors": ["Decision must be an object."]}

    for key in ["id", "title", "decision", "status", "reason"]:
        if not str(decision.get(key) or "").strip():
            errors.append(f"{key} is required.")

    status = str(decision.get("status") or "").lower()
    if status not in VALID_DECISION_STATUSES:
        errors.append("Decision status is invalid.")

    if not isinstance(decision.get("evidence_keys") or [], list):
        errors.append("evidence_keys must be a list.")

    return {"valid": len(errors) == 0, "errors": errors}


def create_decision(
    *,
    decision_id: str,
    title: str,
    decision_text: str,
    reason: str,
    goal_id: str | None = None,
    plan_id: str | None = None,
    alternatives: List[Dict[str, Any]] | None = None,
    evidence_keys: List[str] | None = None,
    source: str = "deterministic_planner",
    confidence: float = 0.8,
    explicit_choice: bool = False,
) -> Dict[str, Any]:
    status = "active" if explicit_choice or source in {"explicit_user_choice", "configured_state"} else "proposed"
    now = utc_now_iso()

    return {
        "id": decision_id,
        "title": title,
        "decision": decision_text,
        "status": status,
        "scope": "project:omega-arc",
        "goal_id": goal_id,
        "plan_id": plan_id,
        "reason": reason,
        "alternatives": deepcopy(alternatives or []),
        "evidence_keys": list(evidence_keys or []),
        "confidence": max(0.0, min(1.0, float(confidence))),
        "source": source,
        "created_at": now,
        "updated_at": now,
        "supersedes": None,
        "superseded_by": None,
    }


def supersede_decision(decision: Dict[str, Any], replacement_id: str) -> Dict[str, Any]:
    updated = deepcopy(decision)
    updated["status"] = "superseded"
    updated["superseded_by"] = replacement_id
    updated["updated_at"] = utc_now_iso()
    return updated


def explain_decision(decision: Dict[str, Any]) -> str:
    title = str(decision.get("title") or "Decision")
    chosen = str(decision.get("decision") or "No decision text recorded.")
    reason = str(decision.get("reason") or "No rationale recorded.")
    status = str(decision.get("status") or "unknown")

    lines = [
        f"Decision: {title}",
        f"Status: {status}",
        f"Chosen path: {chosen}",
        f"Reason: {reason}",
    ]

    alternatives = decision.get("alternatives") or []
    if alternatives:
        lines.append("Alternatives considered:")
        for alternative in alternatives:
            if not isinstance(alternative, dict):
                continue
            value = alternative.get("value")
            why_not = alternative.get("reason_not_selected")
            lines.append(f"- {value}: {why_not}")

    return "\n".join(lines)


def find_decisions_for_goal(decisions: List[Dict[str, Any]], goal_id: str) -> List[Dict[str, Any]]:
    return [
        deepcopy(item)
        for item in decisions
        if isinstance(item, dict) and str(item.get("goal_id")) == str(goal_id)
    ]


def find_decisions_for_plan(decisions: List[Dict[str, Any]], plan_id: str) -> List[Dict[str, Any]]:
    return [
        deepcopy(item)
        for item in decisions
        if isinstance(item, dict) and str(item.get("plan_id")) == str(plan_id)
    ]
