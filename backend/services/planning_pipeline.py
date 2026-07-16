from __future__ import annotations

import re
from typing import Any, Dict, List

from services.planning_engine import build_plan


PLANNING_INTENT_PATTERN = re.compile(
    r"\b(plan|planning|roadmap|next\s+steps|sequence|dependency|dependencies|blocker|blockers)\b",
    re.IGNORECASE,
)


def should_run_planning(user_message: str) -> bool:
    text = str(user_message or "").strip()
    if not text:
        return False
    return bool(PLANNING_INTENT_PATTERN.search(text))


def render_plan_response(plans: List[Dict[str, Any]]) -> str:
    if not plans:
        return "Current Goal\nNone\n\nCurrent Plan\nNo planning steps available.\n\nCurrent Blockers\nNone\n\nConfidence\n0.00"

    sections: List[str] = []
    for plan in plans:
        goal = str(plan.get("goal") or "Unknown goal")
        steps = list(plan.get("steps") or [])
        blockers = list(plan.get("blockers") or [])
        confidence = float(plan.get("confidence") or 0.0)

        sections.append("Current Goal")
        sections.append(goal)
        sections.append("")

        sections.append("Current Plan")
        if steps:
            for index, step in enumerate(steps, start=1):
                sections.append(f"{index}. {step.get('title')}")
        else:
            sections.append("No remaining steps.")
        sections.append("")

        sections.append("Current Blockers")
        if blockers:
            for blocker in blockers:
                sections.append(f"- {blocker}")
        else:
            sections.append("None")
        sections.append("")

        sections.append("Confidence")
        sections.append(f"{confidence:.2f}")

    return "\n".join(sections)


def run_planning_pipeline(
    *,
    user_message: str,
    goal_store: Dict[str, Any],
    evidence_store: Dict[str, Any],
    reasoning_result: Dict[str, Any],
    enabled: bool = True,
) -> Dict[str, Any]:
    if not enabled or not should_run_planning(user_message):
        return {
            "used": False,
            "plans": [],
            "response": None,
            "blockers": [],
        }

    goals = goal_store.get("goals", []) if isinstance(goal_store, dict) else []
    plans = build_plan(goals, evidence_store, reasoning_result)
    plan_dicts = [plan.to_dict() for plan in plans]
    blockers: List[str] = []
    for plan in plan_dicts:
        blockers.extend(list(plan.get("blockers") or []))

    return {
        "used": True,
        "plans": plan_dicts,
        "response": render_plan_response(plan_dicts),
        "blockers": blockers,
    }
