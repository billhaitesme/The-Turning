from __future__ import annotations

import re
from typing import Any, Dict, List

# The cognition layer may only preserve explicitly shared, non-sensitive information.
# It must not store secrets, credentials, or intimate personal details.

COGNITION_VERSION = 1

SENSITIVE_MARKERS = (
    "api key",
    "password",
    "private key",
    "secret token",
    "access token",
    "credit card",
    "social security",
)

CORRECTION_MARKERS = (
    "actually",
    "that is incorrect",
    "that's incorrect",
    "that was wrong",
    "you are wrong",
    "i meant",
    "correction:",
    "not ",
    "instead",
)

PROJECT_PATTERNS = (
    r"\bi am building\s+([A-Za-z0-9][A-Za-z0-9 _\-]{1,80})",
    r"\bi'm building\s+([A-Za-z0-9][A-Za-z0-9 _\-]{1,80})",
    r"\bi am working on\s+([A-Za-z0-9][A-Za-z0-9 _\-]{1,80})",
    r"\bi'm working on\s+([A-Za-z0-9][A-Za-z0-9 _\-]{1,80})",
    r"\bmy project is\s+([A-Za-z0-9][A-Za-z0-9 _\-]{1,80})",
)

GOAL_PATTERNS = (
    r"\bmy goal is to\s+(.+)",
    r"\bi want to\s+(.+)",
    r"\bi plan to\s+(.+)",
    r"\bwe need to\s+(.+)",
    r"\blet's\s+(.+)",
)

PORT_PATTERN = re.compile(
    r"\b(?:backend|server|api)\s+"
    r"(?:runs|is running|listens)\s+"
    r"(?:on\s+)?(?:port\s+)?(\d{2,5})\b",
    re.IGNORECASE,
)


def empty_cognition_result() -> Dict[str, Any]:
    return {
        "version": COGNITION_VERSION,
        "identity_candidates": [],
        "memory_candidates": [],
        "goal_candidates": [],
        "knowledge_candidates": [],
        "corrections": [],
        "curiosity_candidates": [],
    }


def contains_sensitive_material(message: str) -> bool:
    lowered = message.lower()

    return any(marker in lowered for marker in SENSITIVE_MARKERS)


def looks_like_correction(message: str) -> bool:
    lowered = message.strip().lower()

    return any(marker in lowered for marker in CORRECTION_MARKERS)


def extract_explicit_projects(message: str) -> List[str]:
    projects: List[str] = []

    for pattern in PROJECT_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)

        if not match:
            continue

        project = match.group(1).strip(" .,!?:;")

        if project:
            projects.append(project)

    return list(dict.fromkeys(projects))


def extract_explicit_goals(message: str) -> List[str]:
    goals: List[str] = []

    for pattern in GOAL_PATTERNS:
        match = re.search(pattern, message.strip(), re.IGNORECASE)

        if not match:
            continue

        goal = match.group(1).strip(" .,!?:;")

        if 3 <= len(goal) <= 240:
            goals.append(goal)

    return list(dict.fromkeys(goals))


def extract_explicit_backend_port(message: str) -> int | None:
    match = PORT_PATTERN.search(message)

    if not match:
        return None

    port = int(match.group(1))

    if 1 <= port <= 65535:
        return port

    return None


def build_cognition_context(
    *,
    goals: Dict[str, Any],
    graph: Dict[str, Any],
    max_goals: int = 3,
    max_nodes: int = 5,
) -> str:
    goal_items = []
    for goal in goals.get("goals", [])[:max_goals]:
        if goal.get("status") != "active":
            continue
        goal_items.append(f"- {goal.get('title', 'Goal')}")

    knowledge_items = []
    for node in graph.get("nodes", [])[:max_nodes]:
        if node.get("type") != "project":
            continue
        knowledge_items.append(f"- {node.get('label', 'Project')}")

    if not goal_items and not knowledge_items:
        return "No relevant cognition context."

    lines = []
    if goal_items:
        lines.append("Active goals:")
        lines.extend(goal_items)

    if knowledge_items:
        lines.append("")
        lines.append("Relevant project knowledge:")
        lines.extend(knowledge_items)

    return "\n".join(lines)


def analyze_message(*, message: str, assistant_response: str = "") -> Dict[str, Any]:
    if contains_sensitive_material(message):
        return empty_cognition_result()

    result = empty_cognition_result()

    projects = extract_explicit_projects(message)

    for project in projects:
        result["knowledge_candidates"].append(
            {
                "kind": "knowledge",
                "key": "active_project",
                "value": project,
                "source": "explicit_user_statement",
                "confidence": 1.0,
                "importance": 0.9,
                "requires_confirmation": False,
            }
        )

        result["goal_candidates"].append(
            {
                "kind": "goal",
                "key": "build_project",
                "value": project,
                "source": "explicit_user_statement",
                "confidence": 0.95,
                "importance": 0.9,
                "requires_confirmation": False,
            }
        )

    goals = extract_explicit_goals(message)

    for goal in goals:
        result["goal_candidates"].append(
            {
                "kind": "goal",
                "key": "explicit_goal",
                "value": goal,
                "source": "explicit_user_statement",
                "confidence": 1.0,
                "importance": 0.8,
                "requires_confirmation": False,
            }
        )

    backend_port = extract_explicit_backend_port(message)

    if backend_port is not None:
        result["knowledge_candidates"].append(
            {
                "kind": "knowledge",
                "key": "backend_port",
                "value": backend_port,
                "source": "explicit_user_statement",
                "confidence": 1.0,
                "importance": 0.8,
                "requires_confirmation": False,
            }
        )

    if looks_like_correction(message):
        result["corrections"].append(
            {
                "kind": "correction",
                "key": "user_correction",
                "value": message.strip(),
                "source": "explicit_user_statement",
                "confidence": 0.9,
                "importance": 0.9,
                "requires_confirmation": False,
            }
        )

    return result
