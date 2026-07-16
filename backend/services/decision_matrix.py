from __future__ import annotations

from typing import Any, Dict, List


CRITERIA_WEIGHTS = {
    "installation_state": "high",
    "dependency_count": "medium",
    "evidence_completeness": "high",
    "implementation_complexity": "medium",
    "estimated_risk": "high",
    "confidence": "high",
}


def _normalize_score(criterion: str, value: Any) -> str:
    text = str(value or "").lower()

    if criterion in {"dependency_count"}:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return "weak"
        if number <= 2:
            return "strong"
        if number <= 5:
            return "moderate"
        return "weak"

    if criterion in {"implementation_complexity", "estimated_risk"}:
        if text == "low":
            return "strong"
        if text == "medium":
            return "moderate"
        return "weak"

    if text in {"strong", "high"}:
        return "strong"
    if text in {"moderate", "medium"}:
        return "moderate"
    if text in {"weak", "low"}:
        return "weak"
    return "weak"


def build_decision_matrix(comparison: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    items = comparison.get("comparison") if isinstance(comparison, dict) else []
    if not isinstance(items, list):
        items = []

    for criterion, weight in CRITERIA_WEIGHTS.items():
        scores: Dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("plan_id") or "Plan")
            criteria = item.get("criteria") if isinstance(item.get("criteria"), dict) else {}
            scores[title] = _normalize_score(criterion, criteria.get(criterion))
        rows.append({"criterion": criterion, "weight": weight, "scores": scores})

    return {
        "rows": rows,
        "selected_plan_id": comparison.get("selected_plan_id") if isinstance(comparison, dict) else None,
    }
