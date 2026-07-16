from __future__ import annotations

from typing import Any, Dict, List

from services.assumption_engine import list_assumptions

VALID_RISK_RATINGS = {"low", "medium", "high"}


def _rating_max(left: str, right: str) -> str:
    order = {"low": 1, "medium": 2, "high": 3}
    return left if order.get(left, 0) >= order.get(right, 0) else right


def assess_plan_risks(
    *,
    plan: Dict[str, Any],
    evidence_store: Dict[str, Any],
    assumption_store: Dict[str, Any],
) -> Dict[str, Any]:
    risks: List[Dict[str, str]] = []
    facts = evidence_store.get("facts", {}) if isinstance(evidence_store, dict) else {}
    if not isinstance(facts, dict):
        facts = {}

    steps = [step for step in plan.get("steps", []) if isinstance(step, dict)] if isinstance(plan, dict) else []
    dependency_count = sum(len(step.get("dependencies") or []) for step in steps)

    selected = facts.get("vision_model_selected") if isinstance(facts.get("vision_model_selected"), dict) else None
    loaded = facts.get("vision_model_loaded") if isinstance(facts.get("vision_model_loaded"), dict) else None

    if selected and (not loaded or str(loaded.get("state_type") or "unknown") not in {"observed", "verified"}):
        risks.append(
            {
                "risk": "Selected model may not fit GPU memory or load in runtime.",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Evaluate an alternative model and run trusted load verification.",
            }
        )

    if dependency_count >= 4:
        risks.append(
            {
                "risk": "Plan has high dependency coupling and may stall on integration steps.",
                "probability": "medium",
                "impact": "medium",
                "mitigation": "Reduce dependency chain depth before end-to-end validation.",
            }
        )

    plan_id = str(plan.get("id") or "") if isinstance(plan, dict) else ""
    assumed_items = [
        item
        for item in list_assumptions(assumption_store)
        if str(item.get("status") or "") == "assumed" and (not plan_id or str(item.get("plan_id") or "") in {"", plan_id})
    ]
    if assumed_items:
        first = assumed_items[0]
        risks.append(
            {
                "risk": f"Assumption remains unverified: {first.get('statement')}",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Collect evidence to verify or invalidate the assumption.",
            }
        )

    if not risks:
        risks.append(
            {
                "risk": "No material delivery risk identified from current deterministic checks.",
                "probability": "low",
                "impact": "low",
                "mitigation": "Continue gathering verification evidence as steps advance.",
            }
        )

    overall = "low"
    for item in risks:
        overall = _rating_max(overall, str(item.get("impact") or "low"))

    return {
        "plan_id": plan.get("id") if isinstance(plan, dict) else None,
        "overall_risk": overall,
        "risks": risks,
    }
