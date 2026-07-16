from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Set

from services.plan_graph import build_plan_graph, validate_acyclic

VALID_PLAN_STATUSES: Set[str] = {
    "proposed",
    "validated",
    "active",
    "blocked",
    "completed",
    "archived",
    "superseded",
}

VALID_STEP_STATUSES: Set[str] = {
    "pending",
    "ready",
    "active",
    "blocked",
    "completed",
    "skipped",
    "invalidated",
}


def _is_timestamp(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    candidate = deepcopy(plan) if isinstance(plan, dict) else {}

    plan_id = str(candidate.get("id") or "").strip()
    goal_id = str(candidate.get("goal_id") or "").strip()
    title = str(candidate.get("title") or "").strip()
    status = str(candidate.get("status") or "").strip().lower()

    if not plan_id:
        errors.append("Plan id is required.")
    if not goal_id:
        errors.append("Goal id is required.")
    if not title:
        errors.append("Plan title is required.")
    if status not in VALID_PLAN_STATUSES:
        errors.append("Plan status is invalid.")

    for ts_key in ("created_at", "updated_at", "completed_at"):
        ts_value = candidate.get(ts_key)
        if ts_value is None:
            continue
        if not _is_timestamp(ts_value):
            errors.append(f"{ts_key} must be a non-empty string when present.")

    progress = candidate.get("progress")
    if progress is not None:
        try:
            progress_value = float(progress)
        except (TypeError, ValueError):
            errors.append("Progress must be numeric when present.")
        else:
            if progress_value < 0.0 or progress_value > 1.0:
                errors.append("Progress must be between 0.0 and 1.0.")

    steps = candidate.get("steps")
    if not isinstance(steps, list):
        steps = []

    step_ids: List[str] = []
    required_incomplete = False
    for step in steps:
        if not isinstance(step, dict):
            errors.append("Each step must be an object.")
            continue

        step_id = str(step.get("id") or "").strip()
        if not step_id:
            errors.append("Step id is required.")
            continue

        if step_id in step_ids:
            errors.append("Step ids must be unique.")
        step_ids.append(step_id)

        step_status = str(step.get("status") or "").strip().lower()
        if step_status not in VALID_STEP_STATUSES:
            errors.append(f"Step {step_id} has invalid status.")

        dependencies = step.get("dependencies")
        if dependencies is None:
            dependencies = []
        if not isinstance(dependencies, list):
            errors.append(f"Step {step_id} dependencies must be a list.")
            dependencies = []

        for dep in dependencies:
            dep_id = str(dep)
            if dep_id == step_id:
                errors.append(f"Step {step_id} cannot depend on itself.")

        required = bool(step.get("required", True))
        completion_rules = step.get("evidence_requirements")
        if required and not isinstance(completion_rules, list):
            errors.append(f"Required step {step_id} must define completion requirements.")

        completion_evidence = step.get("completion_evidence")
        if step_status == "completed":
            if not isinstance(completion_evidence, list) or len(completion_evidence) == 0:
                errors.append(f"Completed step {step_id} must have completion evidence.")

        blockers = step.get("blockers")
        if step_status == "blocked":
            if not isinstance(blockers, list) or len(blockers) == 0:
                errors.append(f"Blocked step {step_id} must have blockers.")

        if required and step_status not in {"completed", "skipped"}:
            required_incomplete = True

    known_step_ids = set(step_ids)
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "")
        for dep in step.get("dependencies") or []:
            if str(dep) not in known_step_ids:
                errors.append(f"Step {step_id} references missing dependency {dep}.")

    graph = build_plan_graph(candidate)
    if not validate_acyclic(graph):
        errors.append("Plan graph must be acyclic.")

    if status == "completed" and required_incomplete:
        errors.append("Completed plans cannot contain incomplete required steps.")

    if status == "superseded" and not candidate.get("superseded_by"):
        warnings.append("Superseded plan should identify superseded_by replacement id.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
