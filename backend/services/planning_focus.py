from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_PLANNING_FOCUS_DIR = Path(__file__).resolve().parents[1] / "data" / "planning_focus_sessions"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _focus_path(session_id: str, base_dir: Path = DEFAULT_PLANNING_FOCUS_DIR) -> Path:
    slug = "".join(ch for ch in str(session_id or "") if ch.isalnum() or ch in {"-", "_"})
    if not slug:
        slug = "unknown-session"
    return base_dir / f"{slug}.json"


def empty_focus(session_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "focused_goal_id": None,
        "focused_plan_id": None,
        "updated_at": None,
    }


def load_session_focus(*, session_id: Optional[str], base_dir: Path = DEFAULT_PLANNING_FOCUS_DIR) -> Dict[str, Any]:
    if not session_id:
        return empty_focus(None)

    path = _focus_path(session_id, base_dir)
    if not path.exists():
        return empty_focus(session_id)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_focus(session_id)

    if not isinstance(data, dict):
        return empty_focus(session_id)

    data.setdefault("session_id", session_id)
    data.setdefault("focused_goal_id", None)
    data.setdefault("focused_plan_id", None)
    data.setdefault("updated_at", None)
    return data


def save_session_focus(
    *,
    session_id: Optional[str],
    focus: Dict[str, Any],
    base_dir: Path = DEFAULT_PLANNING_FOCUS_DIR,
) -> None:
    if not session_id:
        return

    path = _focus_path(session_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "session_id": session_id,
        "focused_goal_id": focus.get("focused_goal_id"),
        "focused_plan_id": focus.get("focused_plan_id"),
        "updated_at": focus.get("updated_at") or _utc_now_iso(),
    }

    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def update_session_focus(
    *,
    session_id: Optional[str],
    focused_goal_id: Optional[str] = None,
    focused_plan_id: Optional[str] = None,
) -> Dict[str, Any]:
    focus = load_session_focus(session_id=session_id)

    if focused_goal_id is not None:
        focus["focused_goal_id"] = focused_goal_id
    if focused_plan_id is not None:
        focus["focused_plan_id"] = focused_plan_id

    focus["updated_at"] = _utc_now_iso()
    save_session_focus(session_id=session_id, focus=focus)
    return focus
