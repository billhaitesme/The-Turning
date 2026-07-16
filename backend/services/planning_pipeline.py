from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from services.decision_engine import create_decision, validate_decision
from services.decision_store import (
    empty_decision_store,
    list_decisions,
    load_decision_store,
    save_decision_store,
    supersede_decision_in_store,
    upsert_decision,
)
from services.goal_engine import canonical_goal_key
from services.planning_focus import load_session_focus, save_session_focus
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

GOAL_DECLARATION_PATTERN = re.compile(r"\b(?:my\s+goal\s+is|goal\s+is|goal:)\s+(?P<title>.+)$", re.IGNORECASE)
VISION_MODEL_CHOICE_PATTERN = re.compile(r"\buse\s+(?P<model>llava(?::7b)?|qwen2\.5-vl)\b", re.IGNORECASE)


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


def _parse_declared_goal(user_message: str) -> Optional[str]:
    match = GOAL_DECLARATION_PATTERN.search(str(user_message or "").strip())
    if not match:
        return None
    return str(match.group("title") or "").strip()


def _goal_matches_message(goal: Dict[str, Any], user_message: str) -> bool:
    goal_key = str(goal.get("canonical_key") or canonical_goal_key(str(goal.get("title") or "")))
    text = str(user_message or "").lower()

    if not text:
        return False

    if goal_key == "add_vision_routing":
        return "vision" in text and "routing" in text

    goal_tokens = [token for token in goal_key.split("_") if token and token not in {"add", "build", "goal"}]
    if not goal_tokens:
        return False
    return all(token in text for token in goal_tokens)


def _priority_rank(goal: Dict[str, Any]) -> int:
    priority = str(goal.get("priority") or "normal").lower()
    if priority == "high":
        return 0
    if priority == "normal":
        return 1
    return 2


def _normalize_duplicate_active_plans(plan_store: Dict[str, Any]) -> Dict[str, Any]:
    store = dict(plan_store)
    plans = list(store.get("plans") or [])
    keyed: Dict[str, List[Dict[str, Any]]] = {}
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        goal_id = str(plan.get("goal_id") or "")
        if not goal_id:
            continue
        keyed.setdefault(goal_id, []).append(plan)

    for goal_id, candidates in keyed.items():
        active = [item for item in candidates if str(item.get("status") or "").lower() in {"active", "validated", "proposed", "blocked"}]
        if len(active) <= 1:
            continue

        active.sort(
            key=lambda item: (
                str(item.get("source") or "") != "deterministic_planner",
                str(item.get("updated_at") or ""),
                str(item.get("id") or ""),
            ),
            reverse=True,
        )

        keeper = active[0]
        for duplicate in active[1:]:
            duplicate["status"] = "archived"
            duplicate["superseded_by"] = keeper.get("id")

    store["plans"] = plans
    return store


def _select_goal(
    *,
    goals: List[Dict[str, Any]],
    plans_by_goal_id: Dict[str, Dict[str, Any]],
    user_message: str,
    focus: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not goals:
        return None

    active_goals = [goal for goal in goals if str(goal.get("status") or "active").lower() in {"active", "in_progress"}]
    if not active_goals:
        return None

    explicitly_referenced = [goal for goal in active_goals if _goal_matches_message(goal, user_message)]
    if explicitly_referenced:
        explicitly_referenced.sort(key=lambda goal: (str(goal.get("updated_at") or ""), str(goal.get("id") or "")), reverse=True)
        return explicitly_referenced[0]

    focused_goal_id = str(focus.get("focused_goal_id") or "")
    if focused_goal_id:
        for goal in active_goals:
            if str(goal.get("id")) == focused_goal_id:
                return goal

    focused_plan_id = str(focus.get("focused_plan_id") or "")
    if focused_plan_id:
        for goal in active_goals:
            plan = plans_by_goal_id.get(str(goal.get("id") or ""))
            if isinstance(plan, dict) and str(plan.get("id") or "") == focused_plan_id:
                return goal

    non_completed = [goal for goal in active_goals if str(goal.get("status") or "").lower() not in {"completed", "archived", "superseded"}]
    if non_completed:
        non_completed.sort(
            key=lambda goal: (
                _priority_rank(goal),
                str(goal.get("updated_at") or ""),
                str(goal.get("id") or ""),
            ),
        )
        return non_completed[0]

    active_goals.sort(key=lambda goal: (str(goal.get("updated_at") or ""), str(goal.get("id") or "")), reverse=True)
    return active_goals[0]


def _parse_explicit_model_choice(user_message: str) -> Optional[Dict[str, str]]:
    match = VISION_MODEL_CHOICE_PATTERN.search(str(user_message or ""))
    if not match:
        return None

    raw = str(match.group("model") or "").lower()
    normalized = "llava:7b" if raw.startswith("llava") else raw
    label = "LLaVA" if normalized.startswith("llava") else normalized
    return {"model": normalized, "label": label}


def run_planning_pipeline(
    *,
    goal_store: Dict[str, Any],
    evidence_store: Dict[str, Any],
    reasoning_result: Dict[str, Any],
    plan_store: Dict[str, Any] | None = None,
    decision_store: Dict[str, Any] | None = None,
    user_message: str = "",
    session_id: Optional[str] = None,
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
        "selected_plan": None,
        "active_plans": [],
        "focus": None,
        "selection_message": None,
    }

    safe_goal_store = goal_store if isinstance(goal_store, dict) else {"version": 1, "goals": []}
    try:
        candidate_goals = safe_goal_store.get("goals", [])
    except Exception:
        candidate_goals = []
    goals = candidate_goals if isinstance(candidate_goals, list) else []

    current_plan_store = plan_store if isinstance(plan_store, dict) else (load_plan_store() if persist else empty_plan_store())
    current_plan_store = _normalize_duplicate_active_plans(current_plan_store)
    current_decision_store = (
        decision_store if isinstance(decision_store, dict) else (load_decision_store() if persist else empty_decision_store())
    )

    focus = load_session_focus(session_id=session_id)
    declared_goal_text = _parse_declared_goal(user_message)
    if declared_goal_text:
        declared_key = canonical_goal_key(declared_goal_text)
        for goal in goals:
            existing_key = str(goal.get("canonical_key") or canonical_goal_key(str(goal.get("title") or "")))
            if existing_key == declared_key:
                focus["focused_goal_id"] = goal.get("id")
                break

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
            elif blocked_steps:
                blocked_steps_sorted = sorted(
                    blocked_steps,
                    key=lambda item: int(item.get("order") or 9999),
                )
                blocker = blocked_steps_sorted[0]
                title = blocker.get("recommended_action") or blocker.get("title") or "Resolve the highest-priority blocker."
                result["next_actions"].append(
                    {
                        "plan_id": plan.get("id"),
                        "goal_id": goal_id,
                        "step_id": blocker.get("id"),
                        "title": title,
                    }
                )

            # Deterministic decision candidates only when an explicit model choice is present.
            records = evidence_store.get("facts") if isinstance(evidence_store, dict) else {}
            if not isinstance(records, dict):
                records = {}

            selected = records.get("vision_model_selected") if isinstance(records.get("vision_model_selected"), dict) else None
            selected_value = selected.get("value") if isinstance(selected, dict) else None
            explicit_model = _parse_explicit_model_choice(user_message)
            goal_key = str(goal.get("canonical_key") or canonical_goal_key(str(goal.get("title") or "")))

            if explicit_model and goal_key == "add_vision_routing":
                existing = list_decisions(current_decision_store, goal_id=goal_id, plan_id=plan.get("id"))
                if not existing:
                    candidate = create_decision(
                        decision_id=f"decision-{goal_id}-vision-model",
                        title=f"Use {explicit_model['label']} for vision routing",
                        decision_text=f"Use {explicit_model['model']} as the initial vision model.",
                        reason=f"{explicit_model['label']} was explicitly selected, but no additional rationale has been recorded.",
                        goal_id=goal_id,
                        plan_id=plan.get("id"),
                        alternatives=[],
                        evidence_keys=["vision_model_selected"] if selected else [],
                        source="explicit_user_choice",
                        confidence=0.9,
                        explicit_choice=True,
                    )
                    validated_decision = validate_decision(candidate)
                    if validated_decision["valid"]:
                        result["decision_candidates"].append(candidate)
                        current_decision_store = upsert_decision(current_decision_store, candidate)
                elif existing and any(str(item.get("status") or "") == "active" for item in existing):
                    pass
            elif goal_key == "add_vision_routing" and selected and isinstance(selected_value, str) and selected_value.strip() and selected_value.strip().lower() not in {"true", "false"}:
                # Keep deterministic candidate suggestions as proposed only when a named model is present.
                existing = list_decisions(current_decision_store, goal_id=goal_id, plan_id=plan.get("id"))
                if not existing:
                    candidate = create_decision(
                        decision_id=f"decision-{goal_id}-vision-model-candidate",
                        title="Vision model selection candidate",
                        decision_text=f"Use {selected_value.strip()} for vision routing.",
                        reason="Named model evidence exists but no explicit user choice was recorded.",
                        goal_id=goal_id,
                        plan_id=plan.get("id"),
                        alternatives=[],
                        evidence_keys=["vision_model_selected"],
                        source="deterministic_planner",
                        confidence=0.7,
                    )
                    if validate_decision(candidate)["valid"]:
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

    focus_before_selection = dict(focus)
    plans_by_goal_id = {str(plan.get("goal_id") or ""): plan for plan in result["plans"] if isinstance(plan, dict)}
    selected_goal = _select_goal(
        goals=goals,
        plans_by_goal_id=plans_by_goal_id,
        user_message=user_message,
        focus=focus,
    )

    if selected_goal:
        selected_plan = plans_by_goal_id.get(str(selected_goal.get("id") or ""))
        if selected_plan:
            result["active_plan"] = selected_plan
            result["selected_plan"] = selected_plan
            focus["focused_goal_id"] = selected_goal.get("id")
            focus["focused_plan_id"] = selected_plan.get("id")

    active_plans = [
        plan
        for plan in result["plans"]
        if str(plan.get("status") or "").lower() in {"active", "blocked", "validated", "proposed"}
    ]
    result["active_plans"] = active_plans

    planning_intent = detect_planning_intent(user_message)
    had_focus_before_selection = bool(
        focus_before_selection.get("focused_goal_id") or focus_before_selection.get("focused_plan_id")
    )
    explicitly_referenced_any = any(_goal_matches_message(goal, user_message) for goal in goals if isinstance(goal, dict))

    if planning_intent == "plan_summary" and len(active_plans) > 1 and not had_focus_before_selection and not explicitly_referenced_any:
        focus = focus_before_selection
        result["active_plan"] = None
        result["selected_plan"] = None

    if not result.get("selected_plan") and len(active_plans) > 1:
        titles = [str(item.get("title") or item.get("id") or "plan") for item in active_plans]
        result["selection_message"] = (
            "You currently have multiple active plans:\n- "
            + "\n- ".join(titles)
            + "\nNo focused plan is set for this session yet."
        )

    # Deterministic next action ordering.
    result["next_actions"] = sorted(
        result["next_actions"],
        key=lambda item: (str(item.get("goal_id") or ""), str(item.get("step_id") or "")),
    )

    if result.get("selected_plan"):
        selected_plan_id = str(result["selected_plan"].get("id") or "")
        result["next_actions"] = [
            item
            for item in result["next_actions"]
            if str(item.get("plan_id") or "") == selected_plan_id
        ] or result["next_actions"]

    if persist:
        try:
            save_plan_store(current_plan_store)
            save_decision_store(current_decision_store)
            save_session_focus(session_id=session_id, focus=focus)
        except Exception:
            # Pipeline persistence must not break chat.
            pass

    result["focus"] = focus

    return result
