from __future__ import annotations

from typing import Any, Dict, Optional


def apply_curiosity_to_response(
    *,
    response: str,
    curiosity_candidate: Optional[Dict[str, Any]],
    enabled: bool,
) -> str:
    if not enabled or not curiosity_candidate:
        return response

    question = curiosity_candidate.get("question", "").strip()
    if not question:
        return response

    if "?" not in response and "?" not in question:
        return response

    if "?" in response:
        return response

    return f"{response.strip()} {question}"


def choose_curiosity_question(
    *,
    user_message: str,
    cognition_result: Dict[str, Any],
    identity_profile: Dict[str, Any] | None = None,
) -> Optional[Dict[str, Any]]:
    identity_profile = identity_profile or {}
    facts = identity_profile.get("facts", {})

    projects = [
        candidate
        for candidate in cognition_result.get("knowledge_candidates", [])
        if candidate.get("key") == "active_project"
    ]

    if projects:
        project = projects[0].get("value")

        return {
            "kind": "curiosity",
            "question": (
                f"Would you like me to remember "
                f"{project} as one of your active projects?"
            ),
            "reason": "project_memory_permission",
            "importance": 0.8,
        }

    lowered = user_message.lower()

    if "call me " in lowered and "name" not in facts:
        return {
            "kind": "curiosity",
            "question": (
                "Would you like me to store that "
                "as your preferred name?"
            ),
            "reason": "name_memory_permission",
            "importance": 0.9,
        }

    return None


def requires_memory_permission(candidate: Dict[str, Any]) -> bool:
    return bool(candidate.get("requires_confirmation", False))
