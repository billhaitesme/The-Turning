from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from services.evidence_engine import normalize_evidence_record, rank_state, is_expired

REASONING_VERSION = 1


def empty_reasoning_result() -> Dict[str, Any]:
    return {
        "version": REASONING_VERSION,
        "resolved_beliefs": [],
        "conflicts": [],
        "uncertainties": [],
        "changes": [],
        "blocked_goals": [],
        "recommended_actions": [],
    }


def _humanize_key(key: str) -> str:
    return str(key).replace("_", " ").strip() or "unknown"


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


def resolve_evidence_record(
    key: str,
    record: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not record:
        return {
            "key": key,
            "value": None,
            "status": "unknown",
            "state_type": "unknown",
            "confidence": 0.0,
            "source": None,
            "evidence_key": key,
            "reason": "No evidence exists.",
        }

    normalized = normalize_evidence_record(record)
    state_type = normalized.get("state_type", "unknown")
    value = normalized.get("value")

    if state_type in (
        "invalidated",
        "expired",
        "unknown",
    ):
        return {
            "key": key,
            "value": None,
            "status": (
                "stale"
                if state_type == "expired"
                else state_type
            ),
            "state_type": state_type,
            "confidence": 0.0,
            "source": normalized.get("source"),
            "evidence_key": key,
            "reason": normalized.get(
                "notes",
                "Evidence is not currently authoritative.",
            ),
        }

    return {
        "key": key,
        "value": value,
        "status": "resolved",
        "state_type": state_type,
        "confidence": float(
            normalized.get("confidence", 0.0)
        ),
        "source": normalized.get("source"),
        "evidence_key": key,
        "reason": (
            "Resolved from the strongest current evidence."
        ),
    }


def resolve_evidence_store(
    evidence_store: Dict[str, Any],
) -> List[Dict[str, Any]]:
    records = _extract_records(evidence_store)

    if not isinstance(records, dict):
        return []

    resolved = []
    for key, record in records.items():
        resolved.append(resolve_evidence_record(key, record))
    return resolved


def _format_belief(record: Dict[str, Any]) -> str:
    key = _humanize_key(str(record.get("key", "unknown"))).capitalize()
    state_type = record.get("state_type", "unknown")
    value = record.get("value")

    if record.get("status") in {"unknown", "stale", "invalidated"}:
        return f"{key} is {record.get('status')}: {record.get('reason')}"

    if state_type == "configured":
        return f"{key} is configured as {value}."
    if state_type == "declared":
        return f"{key} is declared as {value}."
    if state_type == "observed":
        return f"{key} is observed as {value}."
    if state_type == "verified":
        return f"{key} is verified as {value}."
    if state_type == "inferred":
        return f"{key} is inferred as {value}."

    return f"{key} is {value}."


def _format_uncertainty(record: Dict[str, Any]) -> str:
    key = _humanize_key(str(record.get("key", "unknown"))).capitalize()
    return f"{key} has status {record.get('status', 'unknown')}: {record.get('reason', '')}".strip()


def _format_conflict(record: Dict[str, Any]) -> str:
    key = _humanize_key(str(record.get("key", "unknown"))).capitalize()
    reason = record.get("reason") or "A conflict exists."
    return f"{key}: {reason}"


def _format_change(record: Dict[str, Any]) -> str:
    key = _humanize_key(str(record.get("key", "unknown"))).capitalize()
    change_type = record.get("change_type", "changed")
    before = record.get("before")
    after = record.get("after")
    return f"{key} {change_type} from {before} to {after}."


def _format_blocked_goal(record: Dict[str, Any]) -> str:
    title = record.get("title") or record.get("goal_id") or "goal"
    blockers = record.get("blockers") or []
    blocker_text = "; ".join(
        f"{blocker.get('key')}: {blocker.get('reason')}"
        for blocker in blockers[:3]
        if isinstance(blocker, dict)
    )
    return f"{title} is blocked: {blocker_text}".strip()


def _format_action(record: Dict[str, Any]) -> str:
    action = record.get("action", "recommendation")
    target = record.get("target", "unknown")
    reason = record.get("reason", "")
    return f"{action} for {target}: {reason}".strip()


def build_reasoning_prompt_context(
    reasoning_result: Dict[str, Any],
    *,
    max_beliefs: int = 8,
    max_conflicts: int = 3,
    max_actions: int = 3,
) -> str:
    lines: List[str] = ["Reasoning summary:"]

    resolved = reasoning_result.get("resolved_beliefs", []) or []
    conflicts = reasoning_result.get("conflicts", []) or []
    uncertainties = reasoning_result.get("uncertainties", []) or []
    changes = reasoning_result.get("changes", []) or []
    blocked_goals = reasoning_result.get("blocked_goals", []) or []
    actions = reasoning_result.get("recommended_actions", []) or []

    resolved_lines = [
        record
        for record in resolved
        if record.get("status") == "resolved"
    ]
    uncertain_lines = [
        record
        for record in uncertainties
        if record.get("status") in {"unknown", "stale", "invalidated"}
    ]

    lines.append("")
    lines.append("Resolved:")
    if resolved_lines:
        for record in resolved_lines[:max_beliefs]:
            lines.append(f"- {_format_belief(record)}")
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("Unknown:")
    if uncertain_lines:
        for record in uncertain_lines[:max_beliefs]:
            lines.append(f"- {_format_uncertainty(record)}")
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("Conflicts:")
    if conflicts:
        for record in conflicts[:max_conflicts]:
            lines.append(f"- {_format_conflict(record)}")
    else:
        lines.append("- None.")

    if changes:
        lines.append("")
        lines.append("Changes:")
        for record in changes[:max_conflicts]:
            lines.append(f"- {_format_change(record)}")

    if blocked_goals:
        lines.append("")
        lines.append("Blocked goals:")
        for record in blocked_goals[:max_conflicts]:
            lines.append(f"- {_format_blocked_goal(record)}")

    lines.append("")
    lines.append("Recommended actions:")
    if actions:
        for record in actions[:max_actions]:
            lines.append(f"- {_format_action(record)}")
    else:
        lines.append("- None.")

    return "\n".join(lines)
