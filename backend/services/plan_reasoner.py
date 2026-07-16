from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple

from services.evidence_engine import normalize_evidence_record


RUNTIME_TRUSTED_STATES = {"observed", "verified"}


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


def _step_index(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for step in plan.get("steps", []) if isinstance(plan, dict) else []:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "").strip()
        if step_id:
            index[step_id] = step
    return index


def _evidence_requirement_satisfied(requirement: Dict[str, Any], records: Dict[str, Dict[str, Any]]) -> Tuple[bool, str, Dict[str, Any]]:
    key = str(requirement.get("key") or "").strip()
    if not key:
        return False, "Missing evidence key requirement.", {}

    record = normalize_evidence_record(records.get(key))
    state_type = str(record.get("state_type") or "unknown")
    value = record.get("value")

    if state_type in {"invalidated", "expired", "unknown"}:
        return False, f"{key} is {state_type}.", {}

    required_states = requirement.get("required_state_types") or []
    required_states = [str(item) for item in required_states]

    if required_states and state_type not in required_states:
        return False, f"{key} has state {state_type}, expected {required_states}.", {}

    # Runtime checks cannot be satisfied by declarations.
    if set(required_states).issubset(RUNTIME_TRUSTED_STATES) and state_type not in RUNTIME_TRUSTED_STATES:
        return False, f"{key} requires trusted runtime evidence.", {}

    if "required_value" in requirement and value != requirement.get("required_value"):
        return False, f"{key} value does not match required value.", {}

    return True, "", {"key": key, "state_type": state_type, "value": value}


def evaluate_step(
    *,
    step: Dict[str, Any],
    plan: Dict[str, Any],
    evidence_store: Dict[str, Any],
    reasoning_result: Dict[str, Any],
) -> Dict[str, Any]:
    _ = reasoning_result
    updated = deepcopy(step)
    records = _extract_records(evidence_store)
    steps = _step_index(plan)

    blockers: List[str] = []
    completion: List[Dict[str, Any]] = []

    for dep in updated.get("dependencies") or []:
        dep_id = str(dep)
        dep_step = steps.get(dep_id)
        if not dep_step:
            blockers.append(f"Missing dependency step: {dep_id}.")
            continue
        dep_status = str(dep_step.get("status") or "").lower()
        if dep_status != "completed":
            blockers.append(f"Dependency {dep_id} is {dep_status or 'not completed'}.")

    for requirement in updated.get("evidence_requirements") or []:
        if not isinstance(requirement, dict):
            blockers.append("Invalid evidence requirement entry.")
            continue
        ok, reason, completion_entry = _evidence_requirement_satisfied(requirement, records)
        if ok:
            completion.append(completion_entry)
        else:
            blockers.append(reason)

    if blockers:
        updated["status"] = "blocked"
        updated["blockers"] = blockers
        updated["completion_evidence"] = []
    elif completion:
        updated["status"] = "completed"
        updated["blockers"] = []
        updated["completion_evidence"] = completion
    else:
        updated["status"] = "ready"
        updated["blockers"] = []
        updated.setdefault("completion_evidence", [])

    return updated


def evaluate_plan(
    *,
    plan: Dict[str, Any],
    evidence_store: Dict[str, Any],
    reasoning_result: Dict[str, Any],
) -> Dict[str, Any]:
    updated_plan = deepcopy(plan)
    steps = [deepcopy(step) for step in list(updated_plan.get("steps") or [])]

    for index, step in enumerate(steps):
        evaluated = evaluate_step(
            step=step,
            plan={**updated_plan, "steps": steps},
            evidence_store=evidence_store,
            reasoning_result=reasoning_result,
        )
        steps[index] = evaluated

    evaluated_steps = steps

    # Re-open completed downstream steps if dependencies are no longer complete.
    step_map = {str(step.get("id")): step for step in evaluated_steps if isinstance(step, dict)}
    for step in evaluated_steps:
        if str(step.get("status") or "") != "completed":
            continue
        for dep in step.get("dependencies") or []:
            dep_step = step_map.get(str(dep))
            if not dep_step:
                continue
            if str(dep_step.get("status") or "") != "completed":
                step["status"] = "invalidated"
                step["blockers"] = [f"Dependency {dep} changed after completion."]
                step["completion_evidence"] = []
                break

    ready_steps = [step for step in evaluated_steps if step.get("status") == "ready"]
    blocked_steps = [step for step in evaluated_steps if step.get("status") == "blocked"]
    completed_steps = [step for step in evaluated_steps if step.get("status") == "completed"]
    uncertainties: List[str] = []

    next_step = None
    if ready_steps:
        ready_steps.sort(key=lambda item: int(item.get("order") or 9999))
        next_step = ready_steps[0]
        next_step["status"] = "active"

    required_steps = [step for step in evaluated_steps if bool(step.get("required", True))]
    all_required_completed = all(
        step.get("status") in {"completed", "skipped"}
        for step in required_steps
    ) if required_steps else False

    if all_required_completed and required_steps:
        updated_plan["status"] = "completed"
    elif blocked_steps and not next_step:
        updated_plan["status"] = "blocked"
    else:
        updated_plan["status"] = "active"

    updated_plan["steps"] = evaluated_steps

    return {
        "plan": updated_plan,
        "ready_steps": ready_steps,
        "blocked_steps": blocked_steps,
        "completed_steps": completed_steps,
        "next_step": next_step,
        "uncertainties": uncertainties,
    }
