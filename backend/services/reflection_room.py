"""Epoch XII — the reflection room: activity digest and cycle records (ADR 0025).

Pure logic only. The digest is the deterministic substrate of every self-observation:
each number is computed from the authoritative stores, so a reflection can always be
compared against what actually happened ("no ungrounded self-narrative"). Composition
(the runtime's voice) and room writes are orchestrated in app.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REFLECTION_SCOPE = "self-reflection"

DEFAULT_REFLECTION_CYCLES_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "reflection_cycles.json"
)


def load_reflection_cycles(path: Path = DEFAULT_REFLECTION_CYCLES_PATH) -> Dict[str, Any]:
    if not Path(path).exists():
        return {"version": 1, "cycles": []}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_reflection_cycles(store: Dict[str, Any], path: Path = DEFAULT_REFLECTION_CYCLES_PATH) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(store, indent=2), encoding="utf-8")


def _in_window(timestamp: Optional[str], since: Optional[str]) -> bool:
    if not timestamp:
        return False
    if not since:
        return True
    return str(timestamp) >= str(since)


def build_digest(
    *,
    since: Optional[str],
    study_cycles: Dict[str, Any],
    supersession_candidates: List[Dict[str, Any]],
    memory_events: List[Dict[str, Any]],
    adapters: Dict[str, Any],
    reflection_cycles: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic activity digest for a window (everything since `since`, or all time).
    Every field is traceable to a store; no model involvement."""
    cycles = [c for c in study_cycles.get("cycles", []) if _in_window(c.get("finished_at"), since)]
    lessons_passed = sorted({c["lesson_id"] for c in cycles if c.get("status") == "passed"})
    lessons_failed = sorted({c["lesson_id"] for c in cycles if c.get("status") == "failed"})
    recalls = [c.get("recall_post", {}).get("score") for c in cycles
               if c.get("recall_post", {}).get("score") is not None]
    comprehensions = [(c.get("comprehension") or {}).get("score") for c in cycles
                      if (c.get("comprehension") or {}).get("score") is not None]

    review_sections = [
        (c.get("comprehension") or {}).get("sections", {}).get("review")
        for c in cycles
        if (c.get("comprehension") or {}).get("sections", {}).get("review") is not None
    ]

    pending = [s for s in supersession_candidates if s.get("status") == "pending"]
    resolved = [s for s in supersession_candidates
                if s.get("status") in ("approved", "rejected") and _in_window(s.get("resolved_at"), since)]

    corrections = [e for e in memory_events if _in_window(e.get("created_at"), since)
                   and e.get("event") in ("rescope", "restore")]

    # Every adapter entry IS the durable record of a gated consolidation run (it carries its
    # approval_id) — tool_requests is operational state and may be reset; the registry is history.
    adapter_entries = adapters.get("adapters", [])
    consolidations = [a for a in adapter_entries if _in_window(a.get("created_at"), since)]
    prior_reflections = len([c for c in reflection_cycles.get("cycles", [])])

    return {
        "window_since": since,
        "study": {
            "cycles": len(cycles),
            "lessons_passed": lessons_passed,
            "lessons_failed": lessons_failed,
            "avg_recall": round(sum(recalls) / len(recalls), 4) if recalls else None,
            "avg_comprehension": round(sum(comprehensions) / len(comprehensions), 4) if comprehensions else None,
            "review_interference_min": min(review_sections) if review_sections else None,
        },
        "memory_governance": {
            "supersessions_pending": len(pending),
            "supersessions_resolved": len(resolved),
            "operator_corrections": len(corrections),
        },
        "consolidation": {
            "gated_runs": len(consolidations),
            "adapters_total": len(adapter_entries),
            "adapters_active": len([a for a in adapter_entries if a.get("status") == "active"]),
        },
        "reflection": {
            "prior_observations": prior_reflections,
        },
    }


def digest_summary_lines(digest: Dict[str, Any]) -> List[str]:
    """Human-readable digest lines — the exact facts the composed observation must stay
    grounded in (they are embedded in the composition prompt and stored as provenance)."""
    s, g, c = digest["study"], digest["memory_governance"], digest["consolidation"]
    lines = [
        f"Study cycles run: {s['cycles']}; lessons passed: {', '.join(s['lessons_passed']) or 'none'};"
        f" failed: {', '.join(s['lessons_failed']) or 'none'}.",
        f"Average recall {s['avg_recall']}, average comprehension {s['avg_comprehension']}"
        f" (worst review-section score {s['review_interference_min']}).",
        f"Memory governance: {g['supersessions_pending']} supersession candidate(s) awaiting the operator,"
        f" {g['supersessions_resolved']} resolved, {g['operator_corrections']} operator correction(s) to my memory.",
        f"Consolidation: {c['gated_runs']} operator-gated run(s); {c['adapters_total']} adapter(s) registered,"
        f" {c['adapters_active']} active.",
        f"Prior self-observations: {digest['reflection']['prior_observations']}.",
    ]
    return lines
