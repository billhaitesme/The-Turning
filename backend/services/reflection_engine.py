from __future__ import annotations

from typing import Any, Dict


def empty_reflection() -> Dict[str, Any]:
    return {
        "version": 1,
        "lessons": [],
        "mistakes": [],
        "confirmed_facts": [],
        "unresolved_questions": [],
        "recommended_actions": [],
    }


def detect_user_correction(message: str) -> bool:
    lowered = message.lower()

    markers = (
        "actually",
        "that is incorrect",
        "that's incorrect",
        "you were wrong",
        "that was wrong",
        "i already told you",
        "no, ",
        "not ",
    )

    return any(marker in lowered for marker in markers)


def reflect_on_turn(
    *,
    user_message: str,
    assistant_response: str,
    cognition_result: Dict[str, Any],
) -> Dict[str, Any]:
    reflection = empty_reflection()

    if detect_user_correction(user_message):
        reflection["mistakes"].append(
            {
                "type": "user_correction",
                "description": user_message.strip(),
                "severity": "high",
            }
        )

        reflection["lessons"].append(
            {
                "type": "avoid_superseded_assumption",
                "description": (
                    "A user correction must override "
                    "earlier inferred information."
                ),
            }
        )

        reflection["recommended_actions"].append(
            {
                "action": "review_conflicting_state",
                "priority": "high",
            }
        )

    for candidate in cognition_result.get("knowledge_candidates", []):
        if candidate.get("source") == "explicit_user_statement":
            reflection["confirmed_facts"].append(candidate)

    return reflection
