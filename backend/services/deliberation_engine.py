from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from services.assumption_engine import list_assumptions
from services.decision_matrix import build_decision_matrix
from services.plan_comparator import compare_candidate_plans
from services.risk_engine import assess_plan_risks


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def deliberate_plan_selection(
    *,
    candidate_plans: List[Dict[str, Any]],
    evidence_store: Dict[str, Any],
    assumption_store: Dict[str, Any],
) -> Dict[str, Any]:
    risk_by_plan: Dict[str, Dict[str, Any]] = {}
    risk_list: List[Dict[str, Any]] = []

    for plan in candidate_plans:
        if not isinstance(plan, dict):
            continue
        assessment = assess_plan_risks(
            plan=plan,
            evidence_store=evidence_store,
            assumption_store=assumption_store,
        )
        plan_id = str(plan.get("id") or "")
        risk_by_plan[plan_id] = assessment
        risk_list.append(assessment)

    comparison = compare_candidate_plans(
        candidate_plans=[plan for plan in candidate_plans if isinstance(plan, dict)],
        evidence_store=evidence_store,
        risk_by_plan=risk_by_plan,
    )
    matrix = build_decision_matrix(comparison)

    selected_plan_id = comparison.get("selected_plan_id")
    selected_plan = next((item for item in candidate_plans if isinstance(item, dict) and str(item.get("id") or "") == str(selected_plan_id)), None)
    assumptions = list_assumptions(assumption_store)
    active_assumptions = [item for item in assumptions if str(item.get("status") or "") == "assumed"]

    explanation = "No recommendation available."
    if selected_plan:
        explanation = (
            f"Recommended plan: {selected_plan.get('title')}. "
            "This recommendation prioritizes stronger installation and evidence completeness, "
            "lower estimated risk, and manageable implementation complexity."
        )

    return {
        "generated_at": utc_now_iso(),
        "candidate_plans": [plan for plan in candidate_plans if isinstance(plan, dict)],
        "risk_assessments": risk_list,
        "comparison": comparison,
        "decision_matrix": matrix,
        "recommendation": {
            "plan_id": selected_plan_id,
            "status": "recommended" if selected_plan_id else "proposed",
            "explanation": explanation,
        },
        "assumptions": {
            "active": active_assumptions,
            "all": assumptions,
        },
        "execution": {
            "enabled": False,
            "note": "Execution remains disabled in Epoch VII.",
        },
    }
