from __future__ import annotations

from typing import Any, Dict, Optional

from services.action_recommender import (
    recommend_actions,
)
from services.change_engine import (
    add_dependency_impacts,
    compare_evidence_snapshots,
)
from services.conflict_engine import (
    detect_dependency_conflicts,
    detect_value_conflicts,
)
from services.evidence_engine import normalize_evidence_record
from services.goal_reasoner import (
    evaluate_goal_blockers,
)
from services.reasoning_engine import (
    empty_reasoning_result,
    resolve_evidence_store,
)


def _records_from_store(evidence_store: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(evidence_store, dict):
        return {}

    records = evidence_store.get("records")
    if isinstance(records, dict):
        return records

    facts = evidence_store.get("facts")
    if isinstance(facts, dict):
        return facts

    return {}


def _dependency_map_from_store(evidence_store: Dict[str, Any]) -> Dict[str, list[str]]:
    dependency_map: Dict[str, list[str]] = {}
    for key, record in _records_from_store(evidence_store).items():
        normalized = normalize_evidence_record(record)
        normalized["key"] = normalized.get("key") or key
        dependencies = normalized.get("dependencies") or []
        for dependency in dependencies:
            dependency_map.setdefault(dependency, []).append(key)
    return dependency_map


def run_reasoning_pipeline(
    *,
    evidence_store: Dict[str, Any],
    goal_store: Optional[Dict[str, Any]] = None,
    previous_evidence_store: Optional[
        Dict[str, Any]
    ] = None,
    dependency_map: Optional[
        Dict[str, list[str]]
    ] = None,
) -> Dict[str, Any]:
    result = empty_reasoning_result()

    resolved = resolve_evidence_store(
        evidence_store
    )

    evidence_records = []
    for key, record in _records_from_store(evidence_store).items():
        normalized = normalize_evidence_record(record)
        normalized["key"] = normalized.get("key") or key
        evidence_records.append(normalized)

    conflicts = detect_value_conflicts(
        evidence_records
    )

    conflicts.extend(
        detect_dependency_conflicts(
            evidence_store
        )
    )

    uncertainties = [
        belief
        for belief in resolved
        if belief.get("status")
        in (
            "unknown",
            "stale",
            "invalidated",
        )
    ]

    changes = []

    if previous_evidence_store is not None:
        changes = compare_evidence_snapshots(
            previous_evidence_store,
            evidence_store,
        )

        changes = add_dependency_impacts(
            changes,
            dependency_map or _dependency_map_from_store(evidence_store),
        )

    blocked_goals = evaluate_goal_blockers(
        goal_store or {"goals": []},
        resolved,
    )

    actions = recommend_actions(
        resolved_beliefs=resolved,
        conflicts=conflicts,
        uncertainties=uncertainties,
        blocked_goals=blocked_goals,
    )

    result.update(
        {
            "resolved_beliefs": resolved,
            "conflicts": conflicts,
            "uncertainties": uncertainties,
            "changes": changes,
            "blocked_goals": blocked_goals,
            "recommended_actions": actions,
        }
    )

    return result


def rebuild_reasoning_after_evidence_ingestion(
    *,
    evidence_store: Dict[str, Any],
    goal_store: Optional[Dict[str, Any]] = None,
    previous_evidence_store: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return run_reasoning_pipeline(
        evidence_store=evidence_store,
        goal_store=goal_store,
        previous_evidence_store=previous_evidence_store,
        dependency_map=None,
    )
