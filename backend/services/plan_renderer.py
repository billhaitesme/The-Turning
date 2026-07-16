from __future__ import annotations

from typing import Any, Dict, List


def _title(value: str) -> str:
    return str(value or "").replace("_", " ").strip().capitalize()


def render_plan(plan: Dict[str, Any]) -> str:
    title = str(plan.get("title") or "Unnamed plan")
    lines: List[str] = [f"Current plan: {title}", ""]

    steps = [step for step in plan.get("steps", []) if isinstance(step, dict)]

    sections = {
        "Completed": [step for step in steps if step.get("status") == "completed"],
        "Active": [step for step in steps if step.get("status") == "active"],
        "Pending": [step for step in steps if step.get("status") in {"pending", "ready"}],
        "Blocked": [step for step in steps if step.get("status") == "blocked"],
    }

    for label, section_steps in sections.items():
        if not section_steps and label != "Blocked":
            continue
        lines.append(f"{label}:")
        if section_steps:
            for step in section_steps:
                lines.append(f"- {step.get('title')}")
        else:
            lines.append("- None.")
        lines.append("")

    next_action = next((step for step in steps if step.get("status") == "active"), None)
    if next_action:
        lines.append("Next action:")
        lines.append(f"- {next_action.get('title')}")

    return "\n".join(lines).strip()


def render_plan_summary(plan: Dict[str, Any]) -> str:
    status = _title(str(plan.get("status") or "unknown"))
    blockers = plan.get("blockers") or []
    blocker_text = "None" if not blockers else "; ".join(str(item) for item in blockers[:2])
    return f"Plan {plan.get('title')}: {status}. Blockers: {blocker_text}."


def render_next_action(planning_result: Dict[str, Any]) -> str:
    actions = planning_result.get("next_actions") or []
    if not actions:
        return "No next action is currently available."
    action = actions[0]
    return f"Next action: {action.get('title')}."


def render_decision(decision: Dict[str, Any]) -> str:
    title = str(decision.get("title") or "Decision")
    reason = str(decision.get("reason") or "No recorded reason.")
    chosen = str(decision.get("decision") or "No selected path recorded.")
    status = _title(str(decision.get("status") or "unknown"))

    lines = [
        f"Decision: {title}",
        f"Status: {status}",
        f"Selected path: {chosen}",
        f"Reason: {reason}",
    ]

    alternatives = decision.get("alternatives") or []
    if alternatives:
        lines.append("Alternatives:")
        for alt in alternatives:
            if not isinstance(alt, dict):
                continue
            lines.append(f"- {alt.get('value')}: {alt.get('reason_not_selected')}")

    return "\n".join(lines)
