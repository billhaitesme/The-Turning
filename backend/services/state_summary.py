from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from services.evidence_engine import normalize_evidence_record


def detect_summary_intent(message: str) -> Optional[str]:
    lowered = str(message or "").strip().lower()
    if not lowered:
        return None

    uncertainty_patterns = [
        r"\bwhat remains uncertain\b",
        r"\bwhat are your current uncertainties\b",
        r"\bcurrent uncertainties\b",
        r"\buncertainties\b",
    ]
    for pattern in uncertainty_patterns:
        if re.search(pattern, lowered):
            return "uncertainty_summary"

    state_patterns = [
        r"\bwhat do you currently know\b",
        r"\bwhat do you know\b",
        r"\bsummarize the current state\b",
        r"\bwhat is the current project status\b",
    ]
    for pattern in state_patterns:
        if re.search(pattern, lowered):
            return "state_summary"

    return None


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


def _humanize_key(key: str) -> str:
    return str(key or "").replace("_", " ").strip()


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_text(value: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _project_items(knowledge_graph: Dict[str, Any]) -> List[str]:
    if not isinstance(knowledge_graph, dict):
        return []

    items: List[str] = []
    for node in knowledge_graph.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        if node.get("type") != "project":
            continue
        label = str(node.get("label") or "").strip()
        if not label:
            continue
        items.append(f"{label} is an active project.")
    return _dedupe(items)


def _project_labels(knowledge_graph: Dict[str, Any]) -> List[str]:
    if not isinstance(knowledge_graph, dict):
        return []

    labels: List[str] = []
    for node in knowledge_graph.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        if node.get("type") != "project":
            continue
        label = str(node.get("label") or "").strip()
        if label:
            labels.append(label)
    return _dedupe(labels)


def _goal_items(goal_store: Dict[str, Any], *, project_labels: Iterable[str]) -> List[str]:
    if not isinstance(goal_store, dict):
        return []

    normalized_projects = {_normalize_text(label) for label in project_labels}
    items: List[str] = []
    for goal in goal_store.get("goals", []) or []:
        if not isinstance(goal, dict):
            continue
        status = str(goal.get("status") or "").lower()
        if status not in {"active", "blocked", "in_progress"}:
            continue
        title = str(goal.get("title") or goal.get("id") or "goal").strip()
        if _normalize_text(title) in normalized_projects:
            continue
        if status == "blocked":
            items.append(f"{title} (blocked pending verification evidence).")
        else:
            items.append(f"{title}.")
    return _dedupe(items)


def _configuration_items(records: Dict[str, Dict[str, Any]]) -> List[str]:
    items: List[str] = []
    for key, raw_record in records.items():
        record = normalize_evidence_record(raw_record)
        state_type = record.get("state_type")
        value = record.get("value")

        if key == "backend_port" and state_type == "configured" and value is not None:
            items.append(f"The backend is configured to use port {value}.")
            continue

        if key.endswith("_installed") and state_type in {"declared", "configured", "inferred", "observed", "verified"} and bool(value):
            subject = _humanize_key(key[: -len("_installed")]).capitalize()
            items.append(f"{subject} is reported as installed.")
            continue

        if state_type == "configured" and value is not None:
            label = _humanize_key(key).capitalize()
            items.append(f"{label} is configured as {value}.")

    return _dedupe(items)


def _reasoning_belief_index(reasoning_result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    beliefs: Dict[str, Dict[str, Any]] = {}
    if not isinstance(reasoning_result, dict):
        return beliefs
    for belief in reasoning_result.get("resolved_beliefs", []) or []:
        if not isinstance(belief, dict):
            continue
        key = belief.get("key")
        if not key:
            continue
        beliefs[str(key)] = belief
    return beliefs


def _runtime_items(records: Dict[str, Dict[str, Any]], reasoning_result: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    beliefs = _reasoning_belief_index(reasoning_result)

    backend_health = beliefs.get("backend_health")
    if backend_health:
        status = backend_health.get("status")
        value = backend_health.get("value")
        state_type = backend_health.get("state_type")

        if status in {"unknown", "stale", "invalidated", "conflicted"}:
            items.append("Backend current health is unknown because no current matching verification exists.")
        elif status == "resolved" and state_type in {"verified", "observed"} and value in {"online", "offline"}:
            items.append(f"Backend health is {value} based on verification evidence.")
        elif status == "resolved" and state_type == "declared" and value in {"online", "offline"}:
            items.append(f"Backend health is reported as {value}; runtime health has not been verified.")
    else:
        raw_backend_health = normalize_evidence_record(records.get("backend_health"))
        if raw_backend_health.get("state_type") in {"declared", "configured", "inferred"}:
            items.append("Backend current health is unknown because no current matching verification exists.")

    return _dedupe(items)


def _dependency_uncertainty_text(key: str) -> Optional[str]:
    mapping = {
        "vision_model_selected": "Vision-model selection has not been verified.",
        "vision_model_loaded": "Vision-model runtime readiness has not been verified.",
        "vision_model_healthy": "Vision-model runtime readiness has not been verified.",
        "vision_router_configured": "Vision-routing configuration has not been verified.",
        "vision_routing_verified": "Vision-routing readiness has not been verified.",
        "vision_routing_ready": "Vision-routing readiness has not been verified.",
        "backend_health": "Backend runtime health has not been independently verified.",
    }
    return mapping.get(key)


def _uncertainty_items(reasoning_result: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    if not isinstance(reasoning_result, dict):
        return items

    for uncertainty in reasoning_result.get("uncertainties", []) or []:
        if not isinstance(uncertainty, dict):
            continue
        key = str(uncertainty.get("key") or "")
        status = str(uncertainty.get("status") or "")
        if status not in {"unknown", "stale", "invalidated", "conflicted"}:
            continue
        mapped = _dependency_uncertainty_text(key)
        if mapped:
            items.append(mapped)
            continue
        label = _humanize_key(key).capitalize() or "State"
        items.append(f"{label} has unresolved evidence.")

    for blocked_goal in reasoning_result.get("blocked_goals", []) or []:
        if not isinstance(blocked_goal, dict):
            continue
        for blocker in blocked_goal.get("blockers", []) or []:
            if not isinstance(blocker, dict):
                continue
            key = str(blocker.get("key") or "")
            mapped = _dependency_uncertainty_text(key)
            if mapped:
                items.append(mapped)
            else:
                label = _humanize_key(key).capitalize() or "Dependency"
                items.append(f"{label} is missing readiness evidence.")

    return _dedupe(items)


def _conflict_items(reasoning_result: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    if not isinstance(reasoning_result, dict):
        return items

    for conflict in reasoning_result.get("conflicts", []) or []:
        if not isinstance(conflict, dict):
            continue
        key = _humanize_key(str(conflict.get("key") or "conflict")).capitalize()
        reason = str(conflict.get("reason") or "Conflict detected.").strip()
        items.append(f"{key}: {reason}")

    return _dedupe(items)


def _collect_unresolved_keys(reasoning_result: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    if not isinstance(reasoning_result, dict):
        return keys

    for uncertainty in reasoning_result.get("uncertainties", []) or []:
        if not isinstance(uncertainty, dict):
            continue
        status = str(uncertainty.get("status") or "")
        if status not in {"unknown", "stale", "invalidated", "conflicted"}:
            continue
        key = str(uncertainty.get("key") or "").strip()
        if key:
            keys.append(key)

    for blocked_goal in reasoning_result.get("blocked_goals", []) or []:
        if not isinstance(blocked_goal, dict):
            continue
        for blocker in blocked_goal.get("blockers", []) or []:
            if not isinstance(blocker, dict):
                continue
            key = str(blocker.get("key") or "").strip()
            if key:
                keys.append(key)

    return _dedupe(keys)


def _recommended_action_from_dependency_key(key: str) -> Optional[str]:
    key = str(key or "").strip()
    if key == "vision_model_selected":
        return "Confirm which vision model will be used."
    if key in {"vision_model_loaded", "vision_model_healthy"}:
        return "Verify that the selected model loads successfully."
    if key in {"vision_router_configured", "vision_routing_verified", "vision_routing_ready"}:
        return "Configure and test the complete vision-routing path."
    if key == "backend_health":
        return "Run a backend health check to verify runtime status."
    return None


def _recommended_action_from_internal(action: Dict[str, Any]) -> Optional[str]:
    action_name = str(action.get("action") or "").strip().lower()
    target = str(action.get("target") or "").strip().lower()

    if action_name == "run_health_check" and target in {"backend", "backend_health"}:
        return "Run a backend health check to verify runtime status."
    if action_name == "resolve_goal_blocker":
        return _recommended_action_from_dependency_key(target)
    if action_name == "review_conflict":
        return "Resolve the conflicting evidence before proceeding."
    if action_name == "refresh_evidence":
        return "Refresh stale evidence to restore an authoritative state."
    return None


def _recommended_action_items(reasoning_result: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    if not isinstance(reasoning_result, dict):
        return items

    unresolved_keys = _collect_unresolved_keys(reasoning_result)
    for key in unresolved_keys:
        candidate = _recommended_action_from_dependency_key(key)
        if candidate:
            items.append(candidate)

    for action in reasoning_result.get("recommended_actions", []) or []:
        if not isinstance(action, dict):
            continue
        candidate = _recommended_action_from_internal(action)
        if candidate:
            items.append(candidate)

    prioritized = _dedupe(items)
    priority_order = {
        "Confirm which vision model will be used.": 1,
        "Verify that the selected model loads successfully.": 2,
        "Configure and test the complete vision-routing path.": 3,
        "Run a backend health check to verify runtime status.": 4,
        "Resolve the conflicting evidence before proceeding.": 5,
        "Refresh stale evidence to restore an authoritative state.": 6,
    }
    prioritized.sort(key=lambda item: (priority_order.get(item, 99), item))
    return prioritized[:3]


def _identity_items(identity_profile: Dict[str, Any]) -> List[str]:
    if not isinstance(identity_profile, dict):
        return []

    facts = identity_profile.get("facts") if isinstance(identity_profile.get("facts"), dict) else {}
    items: List[str] = []
    for key, value in facts.items():
        if not isinstance(value, dict):
            continue
        fact_value = value.get("value")
        if fact_value is None:
            continue
        source = value.get("source")
        label = _humanize_key(str(key)).capitalize()
        items.append(f"{label}: {fact_value} (source: {source}).")

    return _dedupe(items)


def build_current_state_summary(
    *,
    identity_profile,
    evidence_store,
    goal_store,
    knowledge_graph,
    reasoning_result,
) -> dict:
    records = _extract_records(evidence_store)
    project_labels = _project_labels(knowledge_graph)

    summary = {
        "identity": _identity_items(identity_profile),
        "projects": _project_items(knowledge_graph),
        "configuration": _configuration_items(records),
        "runtime_state": _runtime_items(records, reasoning_result or {}),
        "goals": _goal_items(goal_store, project_labels=project_labels),
        "uncertainties": _uncertainty_items(reasoning_result or {}),
        "conflicts": _conflict_items(reasoning_result or {}),
        "recommended_actions": _recommended_action_items(reasoning_result or {}),
    }

    return summary


def select_summary_for_intent(summary: Dict[str, Any], intent: str) -> Dict[str, Any]:
    if not isinstance(summary, dict):
        return {
            "identity": [],
            "projects": [],
            "configuration": [],
            "runtime_state": [],
            "goals": [],
            "uncertainties": [],
            "conflicts": [],
            "recommended_actions": [],
        }

    if intent == "uncertainty_summary":
        return {
            "_intent": "uncertainty_summary",
            "identity": [],
            "projects": [],
            "configuration": [],
            "runtime_state": [],
            "goals": [],
            "uncertainties": list(summary.get("uncertainties", []) or []),
            "conflicts": list(summary.get("conflicts", []) or []),
            "recommended_actions": list(summary.get("recommended_actions", []) or []),
        }

    return summary


def render_current_state_summary(summary: dict) -> str:
    if not isinstance(summary, dict):
        return "Current known state:\n- No structured state is available."

    section_specs = [
        ("identity", "Identity"),
        ("projects", "Project"),
        ("configuration", "Configuration"),
        ("runtime_state", "Runtime state"),
        ("goals", "Goals"),
        ("uncertainties", "Uncertainties"),
        ("conflicts", "Conflicts"),
        ("recommended_actions", "Recommended actions"),
    ]

    header = "Current uncertainties:" if summary.get("_intent") == "uncertainty_summary" else "Current known state:"
    lines: List[str] = [header]

    for key, title in section_specs:
        items = summary.get(key) or []
        if not isinstance(items, list) or not items:
            continue
        lines.append("")
        lines.append(f"{title}:")
        for item in items:
            lines.append(f"- {str(item).strip()}")

    if len(lines) == 1:
        lines.append("- No structured state is available.")

    return "\n".join(lines)
