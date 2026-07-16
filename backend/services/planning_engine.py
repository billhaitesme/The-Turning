from __future__ import annotations

from typing import Any, Dict, List, Tuple

from services.goal_engine import infer_goal_requirements
from services.planning_graph import build_plan_graph
from services.planning_models import Plan, PlanDependency, PlanStep


def _extract_records(store: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(store, dict):
        return {}

    records = store.get("records")
    if isinstance(records, dict):
        return records

    facts = store.get("facts")
    if isinstance(facts, dict):
        return facts

    return {}


def _belief_index(reasoning: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(reasoning, dict):
        return {}

    beliefs = reasoning.get("resolved_beliefs")
    if not isinstance(beliefs, list):
        return {}

    index: Dict[str, Dict[str, Any]] = {}
    for belief in beliefs:
        if not isinstance(belief, dict):
            continue
        key = str(belief.get("key") or "").strip()
        if not key:
            continue
        index[key] = belief

    return index


def _humanize_key(key: str) -> str:
    return str(key).replace("_", " ").strip().capitalize()


def _step_title_for_dependency(dependency_key: str) -> str:
    mapping = {
        "vision_model_selected": "Select a vision model",
        "vision_model_loaded": "Verify the model loads correctly",
        "vision_model_healthy": "Verify the model health",
        "vision_router_configured": "Configure the routing pipeline",
        "vision_routing_verified": "Run an end-to-end routing test",
    }
    return mapping.get(dependency_key, f"Verify {_humanize_key(dependency_key).lower()}")


def _dependency_satisfied(
    dependency_key: str,
    *,
    evidence_records: Dict[str, Dict[str, Any]],
    resolved_beliefs: Dict[str, Dict[str, Any]],
) -> Tuple[bool, str]:
    belief = resolved_beliefs.get(dependency_key)
    if isinstance(belief, dict):
        status = str(belief.get("status") or "").lower()
        state_type = str(belief.get("state_type") or "").lower()
        value = belief.get("value")

        if status in {"unknown", "stale", "invalidated"}:
            return False, f"{_humanize_key(dependency_key)} has status {status}."
        if value is False:
            return False, f"{_humanize_key(dependency_key)} is explicitly false."
        if state_type not in {"observed", "verified"}:
            return False, f"{_humanize_key(dependency_key)} is not verified runtime evidence."
        if value in {None, "", 0}:
            return False, f"{_humanize_key(dependency_key)} has no usable value."
        return True, ""

    record = evidence_records.get(dependency_key)
    if not isinstance(record, dict):
        return False, f"Missing dependency evidence: {_humanize_key(dependency_key)}."

    state_type = str(record.get("state_type") or "unknown").lower()
    value = record.get("value")
    if value is False:
        return False, f"{_humanize_key(dependency_key)} is explicitly false."
    if state_type not in {"observed", "verified"}:
        return False, f"{_humanize_key(dependency_key)} is {state_type}, not verified runtime evidence."
    if value in {None, "", 0}:
        return False, f"{_humanize_key(dependency_key)} has no usable value."
    return True, ""


def _active_goals(goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    active: List[Dict[str, Any]] = []
    for goal in goals:
        if not isinstance(goal, dict):
            continue
        status = str(goal.get("status") or "active").lower()
        if status in {"active", "in_progress"}:
            active.append(goal)
    return active


def _plan_confidence(*, total: int, satisfied: int, blocker_count: int) -> float:
    if total <= 0:
        return 0.5

    progress = float(satisfied) / float(total)
    confidence = 0.55 + (0.4 * progress) - (0.1 * float(blocker_count))
    return max(0.05, min(0.99, round(confidence, 2)))


def build_plan(
    goals: List[Dict[str, Any]],
    evidence: Dict[str, Any],
    reasoning: Dict[str, Any],
) -> List[Plan]:
    evidence_records = _extract_records(evidence)
    belief_index = _belief_index(reasoning)

    plans: List[Plan] = []
    for goal in _active_goals(goals):
        goal_id = str(goal.get("id") or "goal-unknown")
        goal_title = str(goal.get("title") or goal_id)

        dependencies = list(goal.get("dependencies") or [])
        if not dependencies:
            inferred = infer_goal_requirements(goal_title)
            dependencies = list(inferred.get("dependencies") or [])

        dependency_models: List[PlanDependency] = []
        unsatisfied_keys: List[str] = []

        for dependency_key in dependencies:
            satisfied, reason = _dependency_satisfied(
                dependency_key,
                evidence_records=evidence_records,
                resolved_beliefs=belief_index,
            )
            dependency_models.append(
                PlanDependency(
                    key=dependency_key,
                    title=_step_title_for_dependency(dependency_key),
                    required_state="verified",
                    satisfied=satisfied,
                    reason=reason,
                )
            )
            if not satisfied:
                unsatisfied_keys.append(dependency_key)

        steps: List[PlanStep] = []
        unresolved_seen = False
        for dependency in dependency_models:
            if dependency.satisfied:
                continue

            status = "blocked" if unresolved_seen else "pending"
            if status == "pending":
                unresolved_seen = True

            step_dependencies: List[str] = []
            index = dependencies.index(dependency.key)
            if index > 0:
                step_dependencies.append(dependencies[index - 1])

            steps.append(
                PlanStep(
                    id=dependency.key,
                    title=dependency.title,
                    status=status,
                    dependencies=step_dependencies,
                    confidence=0.65 if status == "pending" else 0.35,
                )
            )

        blockers = [
            dependency.reason
            for dependency in dependency_models
            if not dependency.satisfied and dependency.reason
        ]

        completed_count = sum(1 for dependency in dependency_models if dependency.satisfied)
        confidence = _plan_confidence(
            total=max(1, len(dependency_models)),
            satisfied=completed_count,
            blocker_count=len(blockers),
        )

        plan_status = "complete"
        if steps and blockers:
            plan_status = "blocked"
        elif steps:
            plan_status = "active"

        step_dicts = [step.to_dict() for step in steps]
        graph = build_plan_graph(goal_id=goal_id, goal_title=goal_title, steps=step_dicts)

        plans.append(
            Plan(
                goal_id=goal_id,
                goal=goal_title,
                status=plan_status,
                confidence=confidence,
                steps=steps,
                blockers=blockers,
                dependencies=dependency_models,
                graph=graph,
            )
        )

    return sorted(plans, key=lambda plan: (plan.goal.lower(), plan.goal_id.lower()))
