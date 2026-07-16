from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.approval_engine import (
    create_approval,
    load_approval_store,
    save_approval_store,
    set_approval_status,
    upsert_approval,
)
from services.assumption_engine import (
    create_assumption,
    empty_assumption_store,
    invalidate_assumption,
    load_assumption_store,
    list_assumptions,
    save_assumption_store,
    upsert_assumption,
)
from services.decision_engine import create_decision, validate_decision
from services.decision_store import (
    empty_decision_store,
    list_decisions,
    save_decision_store,
    supersede_decision_in_store,
    upsert_decision,
)
from services.deliberation_engine import deliberate_plan_selection

DEFAULT_DELIBERATION_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "deliberations.json"

DELIBERATION_INTENTS = {
    "assumption_invalidation": re.compile(
        r"\b(assumption[^.!?]*\b(wrong|invalid|invalidated|false)|wrong\s+assumption|gpu\s+memory\s+assumption\s+was\s+wrong)\b",
        re.IGNORECASE,
    ),
    "deliberation_summary": re.compile(
        r"\b(deliberation|which\s+plan|recommended\s+plan|compare(?:\s+the\s+available)?\s+plans?|trade\s*offs?|why\s+is\s+this\s+plan\s+recommended)\b",
        re.IGNORECASE,
    ),
    "alternative_plan": re.compile(r"\b(another\s+approach|alternative\s+plan|show\s+me\s+another\s+approach)\b", re.IGNORECASE),
    "assumptions": re.compile(r"\b(assumptions?)\b", re.IGNORECASE),
    "risks": re.compile(r"\b(risks?)\b", re.IGNORECASE),
    "approval": re.compile(r"\b(approve|approved|i\s+approve)\b", re.IGNORECASE),
}


MODEL_ALTERNATIVES = [
    {"id_suffix": "llava", "label": "Use LLaVA", "model": "llava:7b"},
    {"id_suffix": "qwen", "label": "Use Qwen2.5-VL", "model": "qwen2.5-vl"},
    {"id_suffix": "minicpm", "label": "Use MiniCPM-V", "model": "minicpm-v"},
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_deliberation_store() -> Dict[str, Any]:
    return {"version": 1, "records": []}


def _normalize_store(store: Any) -> Dict[str, Any]:
    if not isinstance(store, dict):
        return empty_deliberation_store()
    normalized = deepcopy(store)
    if not isinstance(normalized.get("version"), int):
        normalized["version"] = 1
    if not isinstance(normalized.get("records"), list):
        normalized["records"] = []
    return normalized


def load_deliberation_store(path: Path = DEFAULT_DELIBERATION_STORE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return empty_deliberation_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_deliberation_store()
    return _normalize_store(data)


def save_deliberation_store(store: Dict[str, Any], path: Path = DEFAULT_DELIBERATION_STORE_PATH) -> None:
    normalized = _normalize_store(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


def detect_deliberation_intent(user_message: str) -> Optional[str]:
    text = str(user_message or "").strip()
    if not text:
        return None
    for name, pattern in DELIBERATION_INTENTS.items():
        if pattern.search(text):
            return name
    return None


def _generate_alternative_plans(active_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    base_steps = deepcopy(active_plan.get("steps") or [])
    base_goal_id = str(active_plan.get("goal_id") or "")
    base_id = str(active_plan.get("id") or "plan")

    for model in MODEL_ALTERNATIVES:
        plan_id = f"{base_id}-alt-{model['id_suffix']}"
        plan = {
            "id": plan_id,
            "goal_id": base_goal_id,
            "title": f"{active_plan.get('title')} ({model['label']})",
            "status": "proposed",
            "version": int(active_plan.get("version") or 1),
            "steps": deepcopy(base_steps),
            "metadata": {
                "source": "deliberation_alternative",
                "candidate_model": model["model"],
                "confidence": 0.65,
            },
            "source": "deterministic_deliberation",
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        candidates.append(plan)

    return candidates


def _upsert_deliberation_record(store: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    updated = _normalize_store(store)
    record_id = str(record.get("id") or "").strip()
    if not record_id:
        return updated

    replaced = False
    for index, existing in enumerate(updated["records"]):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("id") or "") != record_id:
            continue
        updated["records"][index] = deepcopy(record)
        replaced = True
        break

    if not replaced:
        updated["records"].append(deepcopy(record))

    return updated


def _ensure_default_assumptions(
    *,
    assumption_store: Dict[str, Any],
    goal_id: str,
    plan_id: str,
) -> Dict[str, Any]:
    existing = [
        item
        for item in assumption_store.get("assumptions", [])
        if isinstance(item, dict) and str(item.get("id") or "") == "assumption_gpu_memory"
    ]
    if existing:
        return assumption_store

    assumption = create_assumption(
        assumption_id="assumption_gpu_memory",
        statement="GPU memory is sufficient for the selected model.",
        status="assumed",
        confidence=0.4,
        supporting_evidence=[],
        invalidated_by=[],
        goal_id=goal_id,
        plan_id=plan_id,
    )
    return upsert_assumption(assumption_store, assumption)


def run_deliberation_pipeline(
    *,
    goal_store: Dict[str, Any],
    planning_result: Dict[str, Any],
    evidence_store: Dict[str, Any],
    user_message: str,
    decision_store: Optional[Dict[str, Any]] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    intent = detect_deliberation_intent(user_message)
    active_plan = (planning_result or {}).get("selected_plan") or (planning_result or {}).get("active_plan")

    result: Dict[str, Any] = {
        "intent": intent,
        "candidate_plans": [],
        "deliberation": None,
        "recommendation": None,
        "approval": None,
        "decision": None,
        "execution_enabled": False,
    }

    if not isinstance(active_plan, dict):
        return result

    goal_id = str(active_plan.get("goal_id") or "")
    plan_id = str(active_plan.get("id") or "")

    assumption_store = load_assumption_store() if persist else empty_assumption_store()
    assumption_store = _ensure_default_assumptions(
        assumption_store=assumption_store,
        goal_id=goal_id,
        plan_id=plan_id,
    )

    if intent == "assumption_invalidation":
        active_assumptions = [item for item in list_assumptions(assumption_store) if str(item.get("status") or "") == "assumed"]
        if active_assumptions:
            target_id = str(active_assumptions[0].get("id") or "")
            assumption_store = invalidate_assumption(
                assumption_store,
                assumption_id=target_id,
                invalidated_by=["user_reported_invalid_assumption"],
            )

    candidate_plans = [deepcopy(active_plan)]
    if intent == "alternative_plan":
        candidate_plans.extend(_generate_alternative_plans(active_plan))

    deliberation = deliberate_plan_selection(
        candidate_plans=candidate_plans,
        evidence_store=evidence_store,
        assumption_store=assumption_store,
    )

    prior_recommendation: Dict[str, Any] = {}
    if intent == "approval" and persist:
        persisted = load_deliberation_store()
        records = persisted.get("records", []) if isinstance(persisted, dict) else []
        for item in reversed(records if isinstance(records, list) else []):
            if not isinstance(item, dict):
                continue
            if str(item.get("goal_id") or "") != goal_id:
                continue
            recommendation_obj = item.get("recommendation")
            if isinstance(recommendation_obj, dict):
                prior_recommendation = recommendation_obj
                break

    recommendation = deliberation.get("recommendation") if isinstance(deliberation, dict) else None
    recommended_plan_id = str((recommendation or {}).get("plan_id") or "")

    if intent == "approval" and prior_recommendation:
        recommendation = prior_recommendation
        recommended_plan_id = str(prior_recommendation.get("plan_id") or "")

    if intent == "alternative_plan" and len(candidate_plans) > 1:
        alternative = next(
            (
                item
                for item in candidate_plans
                if isinstance(item, dict) and str(item.get("id") or "") != plan_id
            ),
            None,
        )
        if isinstance(alternative, dict):
            recommended_plan_id = str(alternative.get("id") or "")
            recommendation = {
                "plan_id": recommended_plan_id,
                "status": "recommended",
                "explanation": (
                    f"Recommended alternative: {alternative.get('title')}. "
                    "Alternative recommendation keeps the current plan intact while surfacing a competing path with explicit trade-offs."
                ),
            }

    approval_store = load_approval_store() if persist else {"version": 1, "approvals": []}
    approval = None
    decision = None

    if recommended_plan_id:
        approval = create_approval(
            approval_id=f"approval-{goal_id}-{recommended_plan_id}",
            goal_id=goal_id,
            plan_id=recommended_plan_id,
            status="recommended",
            rationale=str((recommendation or {}).get("explanation") or ""),
        )
        approval_store = upsert_approval(approval_store, approval)

    if intent == "approval" and approval is not None:
        approval_store = set_approval_status(
            approval_store,
            approval_id=str(approval.get("id") or ""),
            status="approved",
            approved_by="user",
        )
        approval = next(
            (
                item
                for item in approval_store.get("approvals", [])
                if isinstance(item, dict) and str(item.get("id") or "") == str(approval.get("id") or "")
            ),
            approval,
        )

        current_decision_store = decision_store if isinstance(decision_store, dict) else (empty_decision_store() if not persist else None)
        if current_decision_store is None:
            from services.decision_store import load_decision_store

            current_decision_store = load_decision_store()

        decision = create_decision(
            decision_id=f"decision-{goal_id}-approved-{recommended_plan_id}",
            title="Approved deliberation recommendation",
            decision_text=f"Approved plan {recommended_plan_id} for goal {goal_id}.",
            reason="User approved the recommended plan after deterministic comparison.",
            goal_id=goal_id,
            plan_id=recommended_plan_id,
            alternatives=[],
            evidence_keys=[],
            source="explicit_user_choice",
            confidence=0.9,
            explicit_choice=True,
        )
        if validate_decision(decision).get("valid"):
            prior_active = [
                item
                for item in list_decisions(current_decision_store, goal_id=goal_id)
                if str(item.get("status") or "") == "active" and str(item.get("id") or "") != str(decision.get("id") or "")
            ]
            if prior_active:
                current_decision_store = supersede_decision_in_store(
                    current_decision_store,
                    old_decision_id=str(prior_active[0].get("id") or ""),
                    new_decision=decision,
                )
            else:
                current_decision_store = upsert_decision(current_decision_store, decision)
            if persist:
                save_decision_store(current_decision_store)

    record = {
        "id": f"deliberation-{goal_id}",
        "goal_id": goal_id,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "candidate_plans": candidate_plans,
        "deliberation": deliberation,
        "recommendation": recommendation,
        "approval": approval,
        "execution_enabled": False,
    }

    deliberation_store = load_deliberation_store() if persist else empty_deliberation_store()
    deliberation_store = _upsert_deliberation_record(deliberation_store, record)

    if persist:
        save_assumption_store(assumption_store)
        save_approval_store(approval_store)
        save_deliberation_store(deliberation_store)

    result["candidate_plans"] = candidate_plans
    result["deliberation"] = deliberation
    result["recommendation"] = recommendation
    result["approval"] = approval
    result["decision"] = decision

    return result
