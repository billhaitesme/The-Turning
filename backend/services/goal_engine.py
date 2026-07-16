from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_GOALS_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "goals.json"
)

VISION_ROUTING_DEPENDENCIES = [
    "vision_model_selected",
    "vision_model_loaded",
    "vision_model_healthy",
    "vision_router_configured",
    "vision_routing_verified",
]


def infer_goal_requirements(title: str) -> Dict[str, Any]:
    lowered = str(title or "").strip().lower()

    if "vision" in lowered and "routing" in lowered:
        return {
            "dependencies": list(VISION_ROUTING_DEPENDENCIES),
            "completion_evidence_key": "vision_routing_ready",
        }

    return {
        "dependencies": [],
        "completion_evidence_key": None,
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    return slug or "goal"


def load_goal_store(path: Path = DEFAULT_GOALS_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 1, "goals": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "goals": []}

    if not isinstance(data, dict):
        return {"version": 1, "goals": []}

    if not isinstance(data.get("goals"), list):
        data["goals"] = []

    data.setdefault("version", 1)

    return data


def save_goal_store(store: Dict[str, Any], path: Path = DEFAULT_GOALS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_goal(
    store: Dict[str, Any],
    *,
    title: str,
    description: Optional[str] = None,
    status: str = "active",
    priority: str = "normal",
    source: str = "explicit_user_statement",
    confidence: float = 1.0,
) -> Dict[str, Any]:
    updated = deepcopy(store)
    updated.setdefault("version", 1)
    updated.setdefault("goals", [])

    goal_id = f"goal-{slugify(title)}"
    now = utc_now_iso()
    requirements = infer_goal_requirements(title)

    for goal in updated["goals"]:
        if goal.get("id") != goal_id:
            continue

        goal["description"] = description or goal.get("description") or title
        goal["status"] = status
        goal["priority"] = priority
        goal["source"] = source
        goal["confidence"] = confidence
        goal["dependencies"] = list(requirements.get("dependencies") or goal.get("dependencies") or [])
        if requirements.get("completion_evidence_key"):
            goal["completion_evidence_key"] = requirements["completion_evidence_key"]
        goal["updated_at"] = now

        return updated

    updated["goals"].append(
        {
            "id": goal_id,
            "title": title,
            "description": description or title,
            "status": status,
            "priority": priority,
            "progress": 0.0,
            "source": source,
            "confidence": confidence,
            "dependencies": list(requirements.get("dependencies") or []),
            "completion_evidence_key": requirements.get("completion_evidence_key"),
            "created_at": now,
            "updated_at": now,
        }
    )

    return updated


def update_goal_progress(
    store: Dict[str, Any],
    *,
    goal_id: str,
    progress: float,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    updated = deepcopy(store)

    normalized_progress = max(0.0, min(1.0, float(progress)))

    for goal in updated.get("goals", []):
        if goal.get("id") != goal_id:
            continue

        goal["progress"] = normalized_progress
        goal["updated_at"] = utc_now_iso()

        if status is not None:
            goal["status"] = status
        elif normalized_progress >= 1.0:
            goal["status"] = "completed"

        return updated

    return updated


def apply_goal_candidates(store: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    updated = store

    for candidate in candidates:
        value = candidate.get("value")

        if not isinstance(value, str):
            continue

        if not value.strip():
            continue

        if candidate.get("requires_confirmation", False):
            continue

        title = value.strip()
        candidate_key = str(candidate.get("key") or "").strip().lower()
        if candidate_key == "build_project":
            lowered = title.lower()
            if lowered.startswith("build "):
                project = title[6:].strip()
            else:
                project = title
            if not project:
                continue
            title = f"Build {project}"

        if not title:
            continue

        updated = upsert_goal(
            updated,
            title=title,
            source=candidate.get("source", "conversation"),
            confidence=float(candidate.get("confidence", 0.5)),
            priority=(
                "high"
                if float(candidate.get("importance", 0.0)) >= 0.8
                else "normal"
            ),
        )

    return updated
