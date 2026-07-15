from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, Optional

SOURCE_PRIORITY = {
    "default": 0,
    "inferred": 1,
    "conversation": 2,
    "explicit_user_statement": 3,
}

AGE_PATTERNS = (
    r"\b(?:i am|i'm|im)\s+(?:actually\s+)?(\d{1,3})\s+years?\s+old\b",
    r"\bmy age is\s+(\d{1,3})\b",
    r"\bi am aged\s+(\d{1,3})\b",
)

def empty_identity_profile() -> Dict[str, Any]:
    return {
        "version": 1,
        "facts": {},
    }

def extract_explicit_age(message: str) -> Optional[int]:
    lowered = message.lower()

    for pattern in AGE_PATTERNS:
        match = re.search(pattern, lowered)

        if not match:
            continue

        age = int(match.group(1))

        if 1 <= age <= 120:
            return age

    return None

def age_group_from_age(age: Optional[int]) -> str:
    if age is None:
        return "unknown"

    if age < 13:
        return "child"

    if age < 18:
        return "teen"

    return "adult"

def should_replace_fact(
    existing: Optional[Dict[str, Any]],
    proposed: Dict[str, Any],
) -> bool:
    if existing is None:
        return True

    existing_priority = SOURCE_PRIORITY.get(
        existing.get("source", "default"),
        0,
    )

    proposed_priority = SOURCE_PRIORITY.get(
        proposed.get("source", "default"),
        0,
    )

    if proposed_priority > existing_priority:
        return True

    if proposed_priority < existing_priority:
        return False

    return float(
        proposed.get("confidence", 0.0)
    ) >= float(
        existing.get("confidence", 0.0)
    )

def set_fact(
    profile: Dict[str, Any],
    *,
    key: str,
    value: Any,
    source: str,
    confidence: float,
) -> Dict[str, Any]:
    if not isinstance(profile, dict):
        profile = empty_identity_profile()

    updated = deepcopy(profile)

    updated.setdefault("version", 1)
    updated.setdefault("facts", {})

    proposed = {
        "value": value,
        "source": source,
        "confidence": max(
            0.0,
            min(1.0, float(confidence)),
        ),
    }

    existing = updated["facts"].get(key)

    if should_replace_fact(existing, proposed):
        updated["facts"][key] = proposed
        updated["version"] = int(
            updated.get("version", 1)
        ) + 1

    return updated

def apply_explicit_identity_updates(
    profile: Dict[str, Any],
    message: str,
) -> Dict[str, Any]:
    updated = normalize_identity_profile(profile)

    explicit_age = extract_explicit_age(message)

    if explicit_age is not None:
        updated = set_fact(
            updated,
            key="age",
            value=explicit_age,
            source="explicit_user_statement",
            confidence=1.0,
        )

    return updated

def normalize_identity_profile(
    raw_profile: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(raw_profile, dict):
        return empty_identity_profile()

    if isinstance(raw_profile.get("facts"), dict):
        return {
            "version": int(
                raw_profile.get("version", 1)
            ),
            "facts": deepcopy(
                raw_profile["facts"]
            ),
        }

    normalized = empty_identity_profile()

    legacy_age = raw_profile.get("age")

    if (
        isinstance(legacy_age, int)
        and 1 <= legacy_age <= 120
    ):
        source = raw_profile.get(
            "age_source",
            "conversation",
        )

        confidence = (
            1.0
            if source == "explicit_user_statement"
            else 0.7
        )

        normalized = set_fact(
            normalized,
            key="age",
            value=legacy_age,
            source=source,
            confidence=confidence,
        )

    return normalized

def build_user_identity_prompt(
    profile: Dict[str, Any],
) -> str:
    normalized = normalize_identity_profile(profile)
    facts = normalized.get("facts", {})
    lines = []

    age_fact = facts.get("age")

    if age_fact:
        age = age_fact.get("value")
        age_group = age_group_from_age(age)

        lines.extend(
            [
                f"- Reported age: {age}",
                f"- Derived age group: {age_group}",
                (
                    "- Age source: "
                    f"{age_fact.get('source', 'unknown')}"
                ),
            ]
        )
    else:
        lines.extend(
            [
                "- Reported age: unknown",
                "- Derived age group: unknown",
                "- Do not guess the user's age.",
                "- Never describe the user as young, old, adult, or any other age group without explicit age facts.",
            ]
        )

    return "\n".join(lines)
