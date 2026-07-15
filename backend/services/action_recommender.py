from __future__ import annotations

from typing import Any, Dict, List


def _append_unique(actions: List[Dict[str, Any]], candidate: Dict[str, Any]) -> None:
    signature = (
        candidate.get("action"),
        candidate.get("target"),
        candidate.get("reason"),
    )
    existing = {
        (
            action.get("action"),
            action.get("target"),
            action.get("reason"),
        )
        for action in actions
    }
    if signature not in existing:
        actions.append(candidate)


def _target_from_key(key: str) -> str:
    lowered = str(key)
    for suffix in ("_health", "_ready", "_status", "_online", "_connected"):
        if lowered.endswith(suffix):
            return lowered[: -len(suffix)]
    return lowered.split("_", 1)[0] if "_" in lowered else lowered


def recommend_actions(
    *,
    resolved_beliefs: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    uncertainties: List[Dict[str, Any]],
    blocked_goals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []

    for uncertainty in uncertainties:
        key = uncertainty.get("key")
        status = uncertainty.get("status")
        if not key:
            continue

        if status in {"unknown", "invalidated"} and ("health" in key or key.endswith("_ready") or key.endswith("_connected")):
            _append_unique(
                actions,
                {
                    "action": "run_health_check",
                    "target": _target_from_key(key),
                    "reason": uncertainty.get("reason") or "Current health is unknown.",
                    "priority": "high",
                    "requires_confirmation": True,
                },
            )
            continue

        if status == "stale":
            _append_unique(
                actions,
                {
                    "action": "refresh_evidence",
                    "target": key,
                    "reason": uncertainty.get("reason") or "Evidence is stale.",
                    "priority": "medium",
                    "requires_confirmation": True,
                },
            )
            continue

        if status == "invalidated":
            _append_unique(
                actions,
                {
                    "action": "review_dependency_change",
                    "target": key,
                    "reason": uncertainty.get("reason") or "Evidence was invalidated.",
                    "priority": "medium",
                    "requires_confirmation": True,
                },
            )
            continue

    for conflict in conflicts:
        key = conflict.get("key")
        if not key:
            continue
        _append_unique(
            actions,
            {
                "action": "review_conflict",
                "target": key,
                "reason": conflict.get("reason") or "A conflict requires review.",
                "priority": "high",
                "requires_confirmation": True,
            },
        )

    for goal in blocked_goals:
        blockers = goal.get("blockers") or []
        if not blockers:
            continue
        blocker = blockers[0]
        _append_unique(
            actions,
            {
                "action": "resolve_goal_blocker",
                "target": blocker.get("key") or goal.get("goal_id"),
                "reason": blocker.get("reason") or "A goal blocker requires attention.",
                "priority": "high",
                "requires_confirmation": True,
            },
        )

    for belief in resolved_beliefs:
        if belief.get("status") != "stale":
            continue
        key = belief.get("key")
        if not key:
            continue
        _append_unique(
            actions,
            {
                "action": "refresh_evidence",
                "target": key,
                "reason": belief.get("reason") or "Evidence is stale.",
                "priority": "medium",
                "requires_confirmation": True,
            },
        )

    return actions
