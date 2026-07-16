from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from services.decision_engine import create_decision, validate_decision
from services.decision_store import (
    empty_decision_store,
    list_decisions,
    load_decision_store,
    save_decision_store,
    upsert_decision,
)
from services.plan_reasoner import evaluate_plan
from services.plan_reviser import revise_plan
from services.plan_store import (
    empty_plan_store,
    find_active_plan_for_goal,
    load_plan_store,
    save_plan_store,
    upsert_plan,
)
from services.plan_validator import validate_plan
from services.planning_engine import generate_plan_for_goal


PLANNING_INTENTS = {
    "plan_summary": re.compile(r"\b(current\s+plan|show\s+me\s+the\s+plan|what\s+is\s+my\s+current\s+plan)\b", re.IGNORECASE),
    "next_plan_action": re.compile(r"\b(what\s+should\s+i\s+do\s+next|next\s+action)\b", re.IGNORECASE),
    "plan_blockers": re.compile(r"\b(what\s+is\s+blocking\s+the\s+plan|plan\s+blockers|blockers?)\b", re.IGNORECASE),
    "decision_explanation": re.compile(r"\b(why\s+did\s+we\s+choose|what\s+decisions?\s+have\s+been\s+made|decisions?)\b", re.IGNORECASE),
    "plan_revision_request": re.compile(r"\b(revise\s+the\s+plan)\b", re.IGNORECASE),
    "alternative_plan_request": re.compile(r"\b(create\s+an\s+alternative\s+plan|alternative\s+plan)\b", re.IGNORECASE),
    "plan_archive_request": re.compile(r"\b(archive\s+this\s+plan|archive\s+plan)\b", re.IGNORECASE),
}


def detect_planning_intent(user_message: str) -> Optional[str]:
    text = str(user_message or "").strip()
    if not text:
        return None
    for intent, pattern in PLANNING_INTENTS.items():
        if pattern.search(text):
            return intent
    return None


def should_create_plan_from_message(user_message: str) -> bool:
    text = str(user_message or "").strip().lower()
    if not text:
        return False

    if detect_planning_intent(text):
        return True

    # Avoid creating plans for ordinary factual questions.
    for phrase in ["what is an api", "explain recursion", "how does http work", "tell me a joke"]:
        if phrase in text:
            return False

    return any(token in text for token in ["plan", "goal", "roadmap", "steps", "routing"])


def run_planning_pipeline(
    *,
    goal_store: Dict[str, Any],
    evidence_store: Dict[str, Any],
    reasoning_result: Dict[str, Any],
    plan_store: Dict[str, Any] | None = None,
    decision_store: Dict[str, Any] | None = None,
    persist: bool = True,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "plans": [],
        "active_plan": None,
        "validation": [],
        "revisions": [],
        "blocked_steps": [],
        "next_actions": [],
        "decision_candidates": [],
    }

    safe_goal_store = goal_store if isinstance(goal_store, dict) else {"version": 1, "goals": []}
    try:
        candidate_goals = safe_goal_store.get("goals", [])
    except Exception:
        candidate_goals = []
    goals = candidate_goals if isinstance(candidate_goals, list) else []

    current_plan_store = plan_store if isinstance(plan_store, dict) else (load_plan_store() if persist else empty_plan_store())
    current_decision_store = (
        decision_store if isinstance(decision_store, dict) else (load_decision_store() if persist else empty_decision_store())
    )

    for goal in goals:
        if not isinstance(goal, dict):
            continue
        status = str(goal.get("status") or "active").lower()
        if status not in {"active", "in_progress"}:
            continue

        goal_id = str(goal.get("id") or "")
        if not goal_id:
            continue

        try:
            plan = find_active_plan_for_goal(current_plan_store, goal_id)
            if not plan:
                plan = generate_plan_for_goal(
                    goal=goal,
                    evidence_store=evidence_store,
                    reasoning_result=reasoning_result,
                )

            validation = validate_plan(plan)
            result["validation"].append({"plan_id": plan.get("id"), **validation})
            if not validation["valid"]:
                plan["status"] = "proposed"

            evaluated = evaluate_plan(
                plan=plan,
                evidence_store=evidence_store,
                reasoning_result=reasoning_result,
            )
            plan = evaluated["plan"]

            revision = revise_plan(
                plan=plan,
                evidence_store=evidence_store,
                reasoning_result=reasoning_result,
            )
            if revision.get("changed"):
                result["revisions"].append(
                    {
                        "plan_id": plan.get("id"),
                        "reason": revision.get("revision_reason"),
                        "invalidated_steps": revision.get("invalidated_steps") or [],
                    }
                )

            plan = revision.get("plan", plan)
            current_plan_store = upsert_plan(current_plan_store, plan)

            blocked_steps = evaluated.get("blocked_steps") or []
            next_step = evaluated.get("next_step")

            result["plans"].append(plan)
            result["blocked_steps"].extend(blocked_steps)
            if next_step:
                result["next_actions"].append(
                    {
                        "plan_id": plan.get("id"),
                        "goal_id": goal_id,
                        "step_id": next_step.get("id"),
                        "title": next_step.get("title"),
                    }
                )

            # Deterministic decision candidates from configured/selected model evidence.
            records = evidence_store.get("facts") if isinstance(evidence_store, dict) else {}
            if not isinstance(records, dict):
                records = {}

            selected = records.get("vision_model_selected") if isinstance(records.get("vision_model_selected"), dict) else None
            if selected:
                existing = list_decisions(current_decision_store, goal_id=goal_id, plan_id=plan.get("id"))
                if not existing:
                    candidate = create_decision(
                        decision_id=f"decision-{goal_id}-vision-model",
                        title="Vision model selection",
                        decision_text=f"Use {selected.get('value')} for vision routing.",
                        reason="Configured or selected model evidence exists.",
                        goal_id=goal_id,
                        plan_id=plan.get("id"),
                        alternatives=[],
                        evidence_keys=["vision_model_selected"],
                        source="deterministic_planner",
                        confidence=0.7,
                    )
                    validated_decision = validate_decision(candidate)
                    if validated_decision["valid"]:
                        result["decision_candidates"].append(candidate)
                        current_decision_store = upsert_decision(current_decision_store, candidate)

        except Exception as exc:
            result["validation"].append(
                {
                    "plan_id": goal_id,
                    "valid": False,
                    "errors": [f"Planning pipeline error: {repr(exc)}"],
                    "warnings": [],
                }
            )

    if result["plans"]:
        result["active_plan"] = sorted(
            result["plans"],
            key=lambda plan: (
                str(plan.get("priority") or "normal") != "high",
                str(plan.get("updated_at") or ""),
                str(plan.get("id") or ""),
            ),
        )[0]

    # Deterministic next action ordering.
    result["next_actions"] = sorted(
        result["next_actions"],
        key=lambda item: (str(item.get("goal_id") or ""), str(item.get("step_id") or "")),
    )

    if persist:
        try:
            save_plan_store(current_plan_store)
            save_decision_store(current_decision_store)
        except Exception:
            # Pipeline persistence must not break chat.
            pass

    return result
