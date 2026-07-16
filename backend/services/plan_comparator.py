from __future__ import annotations

from typing import Any, Dict, List


def _state_rank(state_type: str) -> int:
    order = {"unknown": 0, "declared": 1, "configured": 2, "observed": 3, "verified": 4}
    return order.get(str(state_type or "unknown"), 0)


def _band_from_ratio(value: float) -> str:
    if value >= 0.75:
        return "strong"
    if value >= 0.4:
        return "moderate"
    return "weak"


def compare_candidate_plans(
    *,
    candidate_plans: List[Dict[str, Any]],
    evidence_store: Dict[str, Any],
    risk_by_plan: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    facts = evidence_store.get("facts", {}) if isinstance(evidence_store, dict) else {}
    if not isinstance(facts, dict):
        facts = {}

    comparisons: List[Dict[str, Any]] = []

    for plan in candidate_plans:
        plan_id = str(plan.get("id") or "")
        steps = [step for step in plan.get("steps", []) if isinstance(step, dict)]

        dep_count = sum(len(step.get("dependencies") or []) for step in steps)
        evidence_reqs = [req for step in steps for req in (step.get("evidence_requirements") or []) if isinstance(req, dict)]
        satisfied = 0
        for req in evidence_reqs:
            key = str(req.get("key") or "")
            record = facts.get(key) if isinstance(facts.get(key), dict) else None
            if record and _state_rank(str(record.get("state_type") or "unknown")) >= 2:
                satisfied += 1

        completeness_ratio = 1.0 if not evidence_reqs else (satisfied / float(len(evidence_reqs)))
        installation_strength = "strong" if _state_rank(str((facts.get("vision_model_installed") or {}).get("state_type") if isinstance(facts.get("vision_model_installed"), dict) else "unknown")) >= 1 else "weak"
        if installation_strength == "weak" and str((facts.get("vision_model_selected") or {}).get("state_type") if isinstance(facts.get("vision_model_selected"), dict) else "unknown") in {"declared", "configured", "observed", "verified"}:
            installation_strength = "moderate"

        complexity = "low" if len(steps) <= 4 and dep_count <= 3 else "medium" if len(steps) <= 7 and dep_count <= 6 else "high"
        risk = str((risk_by_plan.get(plan_id) or {}).get("overall_risk") or "medium")

        confidence = float((plan.get("metadata") or {}).get("confidence") or 0.6)
        confidence_band = "high" if confidence >= 0.75 else "medium" if confidence >= 0.45 else "low"

        comparisons.append(
            {
                "plan_id": plan_id,
                "title": str(plan.get("title") or plan_id or "Candidate Plan"),
                "criteria": {
                    "installation_state": installation_strength,
                    "dependency_count": dep_count,
                    "evidence_completeness": _band_from_ratio(completeness_ratio),
                    "implementation_complexity": complexity,
                    "estimated_risk": risk,
                    "confidence": confidence_band,
                },
            }
        )

    def _plan_rank(item: Dict[str, Any]) -> tuple:
        c = item.get("criteria") or {}
        strength = {"weak": 0, "moderate": 1, "strong": 2}
        risk_rank = {"high": 0, "medium": 1, "low": 2}
        confidence_rank = {"low": 0, "medium": 1, "high": 2}
        complexity_rank = {"high": 0, "medium": 1, "low": 2}
        return (
            strength.get(str(c.get("installation_state") or "weak"), 0),
            strength.get(str(c.get("evidence_completeness") or "weak"), 0),
            risk_rank.get(str(c.get("estimated_risk") or "high"), 0),
            confidence_rank.get(str(c.get("confidence") or "low"), 0),
            complexity_rank.get(str(c.get("implementation_complexity") or "high"), 0),
            -int(c.get("dependency_count") or 0),
            str(item.get("plan_id") or ""),
        )

    ranking = sorted(comparisons, key=_plan_rank, reverse=True)
    selected_plan_id = ranking[0]["plan_id"] if ranking else None

    return {
        "comparison": comparisons,
        "ranking": [item.get("plan_id") for item in ranking],
        "selected_plan_id": selected_plan_id,
    }
