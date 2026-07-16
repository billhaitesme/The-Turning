from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Tuple

from services.goal_engine import infer_goal_requirements
from services.plan_graph import build_plan_graph
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return token or "goal"


def _build_step(
    *,
    step_id: str,
    title: str,
    description: str,
    order: int,
    dependencies: List[str],
    evidence_key: str,
    required_state_types: List[str],
    required_value: Any = True,
    recommended_action: str,
    required: bool = True,
) -> Dict[str, Any]:
    now = _utc_now_iso()
    return {
        "id": step_id,
        "title": title,
        "description": description,
        "status": "pending",
        "order": order,
        "required": required,
        "dependencies": list(dependencies),
        "evidence_requirements": [
            {
                "key": evidence_key,
                "required_state_types": list(required_state_types),
                "required_value": required_value,
            }
        ],
        "completion_evidence": [],
        "blockers": [],
        "recommended_action": recommended_action,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }


def _vision_routing_steps() -> List[Dict[str, Any]]:
    return [
        _build_step(
            step_id="select-vision-model",
            title="Select the vision model",
            description="Choose the model that will receive image-based requests.",
            order=1,
            dependencies=[],
            evidence_key="vision_model_selected",
            required_state_types=["declared", "configured", "observed", "verified"],
            recommended_action="Confirm which vision model will be used.",
        ),
        _build_step(
            step_id="verify-vision-model-load",
            title="Verify that the model loads successfully",
            description="Confirm the selected model can load in the runtime environment.",
            order=2,
            dependencies=["select-vision-model"],
            evidence_key="vision_model_loaded",
            required_state_types=["observed", "verified"],
            recommended_action="Run a trusted load verification for the selected model.",
        ),
        _build_step(
            step_id="verify-vision-model-response",
            title="Verify the model responds to a basic vision request",
            description="Validate a minimal vision inference path using the selected model.",
            order=3,
            dependencies=["verify-vision-model-load"],
            evidence_key="vision_model_responding",
            required_state_types=["observed", "verified"],
            recommended_action="Run a basic vision request and capture verification evidence.",
        ),
        _build_step(
            step_id="configure-routing-rule",
            title="Configure the routing rule",
            description="Configure routing so vision requests are directed to the selected model.",
            order=4,
            dependencies=["select-vision-model"],
            evidence_key="vision_router_configured",
            required_state_types=["configured", "observed", "verified"],
            recommended_action="Apply and verify routing configuration for vision traffic.",
        ),
        _build_step(
            step_id="run-end-to-end-routing-test",
            title="Run an end-to-end routing test",
            description="Verify routing, model response, and output integrity in a full path test.",
            order=5,
            dependencies=["verify-vision-model-response", "configure-routing-rule"],
            evidence_key="vision_routing_verified",
            required_state_types=["observed", "verified"],
            recommended_action="Run an end-to-end routing test and capture verification evidence.",
        ),
        _build_step(
            step_id="review-evidence-and-update-goal",
            title="Review evidence and update the goal status",
            description="Review all verification evidence and confirm goal status is current.",
            order=6,
            dependencies=["run-end-to-end-routing-test"],
            evidence_key="vision_routing_ready",
            required_state_types=["verified"],
            recommended_action="Review final evidence and update goal status explicitly.",
        ),
    ]


def _generic_steps() -> List[Dict[str, Any]]:
    return [
        _build_step(
            step_id="define-success-criteria",
            title="Define success criteria",
            description="Establish explicit success criteria for the goal.",
            order=1,
            dependencies=[],
            evidence_key="success_criteria_defined",
            required_state_types=["declared", "configured", "observed", "verified"],
            recommended_action="Define objective success criteria for this goal.",
        ),
        _build_step(
            step_id="identify-dependencies",
            title="Identify dependencies",
            description="Identify prerequisite dependencies and required conditions.",
            order=2,
            dependencies=["define-success-criteria"],
            evidence_key="dependencies_identified",
            required_state_types=["declared", "configured", "observed", "verified"],
            recommended_action="List all critical dependencies required by this goal.",
        ),
        _build_step(
            step_id="resolve-missing-evidence",
            title="Resolve missing evidence",
            description="Collect and verify missing evidence needed to proceed.",
            order=3,
            dependencies=["identify-dependencies"],
            evidence_key="missing_evidence_resolved",
            required_state_types=["observed", "verified"],
            recommended_action="Collect missing evidence and verify unresolved assumptions.",
        ),
        _build_step(
            step_id="perform-implementation-manually",
            title="Perform the implementation manually",
            description="Carry out implementation steps outside the planner.",
            order=4,
            dependencies=["resolve-missing-evidence"],
            evidence_key="manual_implementation_completed",
            required_state_types=["observed", "verified"],
            recommended_action="Perform the implementation manually and record outcomes.",
        ),
        _build_step(
            step_id="verify-result",
            title="Verify the result",
            description="Verify the implementation outcome with trusted evidence.",
            order=5,
            dependencies=["perform-implementation-manually"],
            evidence_key="result_verified",
            required_state_types=["observed", "verified"],
            recommended_action="Run deterministic verification and capture evidence.",
        ),
        _build_step(
            step_id="review-and-update-goal",
            title="Review and update the goal",
            description="Review verification evidence and update goal status explicitly.",
            order=6,
            dependencies=["verify-result"],
            evidence_key="goal_reviewed",
            required_state_types=["declared", "configured", "observed", "verified"],
            recommended_action="Review evidence and update the goal state explicitly.",
        ),
    ]


def generate_plan_for_goal(
    *,
    goal: Dict[str, Any],
    evidence_store: Dict[str, Any],
    reasoning_result: Dict[str, Any],
) -> Dict[str, Any]:
    _ = evidence_store
    _ = reasoning_result

    goal_id = str(goal.get("id") or f"goal-{_slug(goal.get('title') or 'goal')}")
    title = str(goal.get("title") or goal_id)
    description = str(goal.get("description") or "")
    priority = str(goal.get("priority") or "normal")

    normalized_title = title.lower().strip()
    use_vision_template = "vision" in normalized_title and "routing" in normalized_title

    steps = _vision_routing_steps() if use_vision_template else _generic_steps()
    source = "deterministic_planner" if use_vision_template else "generic_deterministic_template"

    now = _utc_now_iso()
    plan_id = f"plan-{_slug(goal_id.replace('goal-', '') or title)}"
    if plan_id == "plan":
        plan_id = f"plan-{_slug(title)}"

    return {
        "id": plan_id,
        "goal_id": goal_id,
        "title": title,
        "description": description or (
            "Select, verify, configure, and test a vision-routing path."
            if use_vision_template
            else "Deterministic bounded plan generated from active goal state."
        ),
        "status": "proposed",
        "priority": priority,
        "version": 1,
        "source": source,
        "confidence": 1.0,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "supersedes": None,
        "superseded_by": None,
        "steps": steps,
        "metadata": {
            "planner_version": 1,
            "reasoning_snapshot_id": None,
            "goal_snapshot": {
                "id": goal_id,
                "title": title,
                "status": goal.get("status"),
            },
        },
    }
