from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from services.evidence_engine import normalize_evidence_record


def _extract_records(evidence_store: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(evidence_store, dict):
        return {}

    records = evidence_store.get("records")
    if isinstance(records, dict):
        return records

    facts = evidence_store.get("facts")
    if isinstance(facts, dict):
        return facts

    return {}


def detect_value_conflicts(
    evidence_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for record in evidence_records:
        key = record.get("key")

        if not key:
            continue

        if record.get("state_type") in (
            "invalidated",
            "expired",
            "unknown",
        ):
            continue

        grouped[key].append(record)

    conflicts: List[Dict[str, Any]] = []

    for key, records in grouped.items():
        values = {
            repr(record.get("value"))
            for record in records
        }

        if len(values) <= 1:
            continue

        conflicts.append(
            {
                "key": key,
                "type": "conflicting_current_values",
                "values": [
                    record.get("value")
                    for record in records
                ],
                "severity": "high",
                "reason": (
                    "Multiple current evidence records "
                    "support different values."
                ),
            }
        )

    return conflicts


def detect_dependency_conflicts(
    evidence_store: Dict[str, Any],
) -> List[Dict[str, Any]]:
    records = _extract_records(evidence_store)
    conflicts: List[Dict[str, Any]] = []

    for key, record in records.items():
        normalized = normalize_evidence_record(record)
        normalized["key"] = normalized.get("key") or key

        dependencies = normalized.get("dependencies") or []
        if not dependencies:
            continue

        current_state = normalized.get("state_type")
        if current_state in {"verified", "observed"}:
            dependency_states = [
                normalize_evidence_record(records.get(dependency, {})).get("state_type")
                for dependency in dependencies
            ]
            if any(state in {"invalidated", "expired", "unknown"} for state in dependency_states):
                conflicts.append(
                    {
                        "key": key,
                        "type": "verification_dependency_mismatch",
                        "values": ["verified", "dependency_changed"],
                        "severity": "high",
                        "reason": (
                            "Runtime verification no longer matches "
                            "the current configuration."
                        ),
                    }
                )
            continue

        if current_state in {"invalidated", "expired"}:
            conflicts.append(
                {
                    "key": key,
                    "type": "verification_dependency_mismatch",
                    "values": [current_state, "dependency_changed"],
                    "severity": "high",
                    "reason": (
                        "Runtime verification no longer matches "
                        "the current configuration."
                    ),
                }
            )

    return conflicts
