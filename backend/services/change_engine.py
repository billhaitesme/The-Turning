from __future__ import annotations

from typing import Any, Dict, List

from services.evidence_engine import normalize_evidence_record, rank_state


def _extract_records(evidence_snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(evidence_snapshot, dict):
        return {}

    records = evidence_snapshot.get("records")
    if isinstance(records, dict):
        return records

    facts = evidence_snapshot.get("facts")
    if isinstance(facts, dict):
        return facts

    return {}


def compare_evidence_snapshots(
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> List[Dict[str, Any]]:
    before_records = _extract_records(before)
    after_records = _extract_records(after)

    changes: List[Dict[str, Any]] = []
    all_keys = sorted(set(before_records) | set(after_records))

    for key in all_keys:
        previous = normalize_evidence_record(before_records.get(key)) if key in before_records else None
        current = normalize_evidence_record(after_records.get(key)) if key in after_records else None

        if previous is None and current is not None:
            changes.append(
                {
                    "key": key,
                    "change_type": "created",
                    "before": None,
                    "after": current.get("value"),
                    "impact": [],
                }
            )
            continue

        if current is None and previous is not None:
            changes.append(
                {
                    "key": key,
                    "change_type": "removed",
                    "before": previous.get("value"),
                    "after": None,
                    "impact": [],
                }
            )
            continue

        if previous is None or current is None:
            continue

        before_state = previous.get("state_type")
        after_state = current.get("state_type")
        before_value = previous.get("value")
        after_value = current.get("value")

        if after_state == "invalidated":
            change_type = "invalidated"
        elif after_state == "expired":
            change_type = "expired"
        elif before_state != after_state and rank_state(after_state) > rank_state(before_state):
            change_type = "promoted"
        elif before_state != after_state and rank_state(after_state) < rank_state(before_state):
            change_type = "demoted"
        elif before_value != after_value:
            change_type = "value_changed"
        else:
            continue

        changes.append(
            {
                "key": key,
                "change_type": change_type,
                "before": before_value,
                "after": after_value,
                "impact": [],
            }
        )

    return changes


def add_dependency_impacts(
    changes: List[Dict[str, Any]],
    dependency_map: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []

    for change in changes:
        impact = list(dict.fromkeys(change.get("impact", [])))
        for dependent in dependency_map.get(change.get("key"), []):
            if dependent not in impact:
                impact.append(dependent)
        updated.append({**change, "impact": impact})

    return updated
