from __future__ import annotations

from typing import Any, Dict, List

from services.evidence_engine import normalize_evidence_record


def _belief_index(resolved_beliefs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        belief.get("key"): belief
        for belief in resolved_beliefs
        if isinstance(belief, dict) and belief.get("key")
    }


def evaluate_goal_blockers(
    goal_store: Dict[str, Any],
    resolved_beliefs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    goals = goal_store.get("goals", []) if isinstance(goal_store, dict) else []
    beliefs = _belief_index(resolved_beliefs)
    blocked_goals: List[Dict[str, Any]] = []

    for goal in goals:
        dependencies = goal.get("dependencies") or []
        if not dependencies:
            continue

        blockers: List[Dict[str, Any]] = []
        for dependency in dependencies:
            belief = beliefs.get(dependency)
            if not belief:
                blockers.append(
                    {
                        "key": dependency,
                        "reason": "Dependency is missing from the current evidence set.",
                    }
                )
                continue

            status = belief.get("status")
            state_type = belief.get("state_type")
            value = belief.get("value")

            if status in {"unknown", "stale", "invalidated"}:
                blockers.append(
                    {
                        "key": dependency,
                        "reason": f"Current evidence is {status}.",
                    }
                )
                continue

            if value is False:
                blockers.append(
                    {
                        "key": dependency,
                        "reason": "Dependency is explicitly false.",
                    }
                )
                continue

            if state_type in {"declared", "configured", "inferred"}:
                blockers.append(
                    {
                        "key": dependency,
                        "reason": "Configured-only readiness does not satisfy runtime requirement.",
                    }
                )
                continue

            if state_type not in {"observed", "verified"}:
                blockers.append(
                    {
                        "key": dependency,
                        "reason": "Dependency is not verified for runtime readiness.",
                    }
                )

        if blockers:
            blocked_goals.append(
                {
                    "goal_id": goal.get("id"),
                    "title": goal.get("title"),
                    "status": "blocked",
                    "blockers": blockers,
                }
            )

    return blocked_goals


def evaluate_goal_completion(
    goal: Dict[str, Any],
    evidence_store: Dict[str, Any],
) -> Dict[str, Any]:
    completion_key = (
        goal.get("completion_evidence_key")
        or goal.get("evidence_key")
        or goal.get("id")
    )

    if isinstance(evidence_store, dict):
        records = evidence_store.get("records") or evidence_store.get("facts") or {}
    else:
        records = {}

    evidence = normalize_evidence_record(records.get(completion_key)) if isinstance(records, dict) else normalize_evidence_record(None)
    evidence_state = evidence.get("state_type")
    evidence_value = evidence.get("value")

    if evidence_state == "verified" and bool(evidence_value):
        return {
            "goal_id": goal.get("id"),
            "title": goal.get("title"),
            "status": "complete",
            "reason": "Verified completion evidence exists.",
            "evidence_key": completion_key,
        }

    if float(goal.get("progress", 0.0)) >= 1.0 or goal.get("status") == "completed":
        return {
            "goal_id": goal.get("id"),
            "title": goal.get("title"),
            "status": "completion_unverified",
            "reason": "Declared completion is not yet verified by evidence.",
            "evidence_key": completion_key,
        }

    return {
        "goal_id": goal.get("id"),
        "title": goal.get("title"),
        "status": "in_progress",
        "reason": "Goal completion has not been established.",
        "evidence_key": completion_key,
    }
