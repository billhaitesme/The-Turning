"""Epoch XI — Tutelage: curriculum store, deterministic chunking, and recall grading.

Pure logic only (no model calls, no direct memory access) so it stays hermetic and
testable. The study-cycle orchestration in app.py injects the memory functions.
See docs/architecture/epoch-xi-tutelage.md and ADR 0013.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

DEFAULT_CURRICULUM_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "curriculum.json"
)
DEFAULT_STUDY_CYCLES_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "study_cycles.json"
)
DEFAULT_ADAPTERS_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "adapters.json"
)
# Lesson source paths are relative to the repository root (backend/..).
REPO_ROOT = Path(__file__).resolve().parents[2]


# Private overlay: operator's-world subjects that must never leave this machine (Tier 3 and
# anything the operator marks private). A store's private twin is always its sibling
# `<name>.private.json` (gitignored) — derived from whatever path is read, so callers that
# point at temp files stay hermetic and public files never absorb private records.
def private_sibling(path: Path) -> Path:
    p = Path(path)
    return p.with_name(f"{p.stem}.private{p.suffix}")


DEFAULT_PRIVATE_CURRICULUM_PATH = private_sibling(DEFAULT_CURRICULUM_PATH)
DEFAULT_PRIVATE_STUDY_CYCLES_PATH = private_sibling(DEFAULT_STUDY_CYCLES_PATH)


def _read_json(path: Path, empty: Dict[str, Any]) -> Dict[str, Any]:
    if not Path(path).exists():
        return dict(empty)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_curriculum(path: Path = DEFAULT_CURRICULUM_PATH) -> Dict[str, Any]:
    curriculum = _read_json(path, {"version": 1, "subjects": []})
    if private_sibling(path).exists():
        private = _read_json(private_sibling(path), {"version": 1, "subjects": []})
        public_ids = {s.get("id") for s in curriculum.get("subjects", [])}
        for subject in private.get("subjects", []):
            if subject.get("id") in public_ids:
                continue  # a public subject wins its id; private never shadows public
            merged = dict(subject)
            merged["private"] = True
            curriculum.setdefault("subjects", []).append(merged)
    return curriculum


def is_private_subject(subject: Optional[Dict[str, Any]]) -> bool:
    return bool(subject and subject.get("private"))


def study_cycles_path_for(subject: Optional[Dict[str, Any]]) -> Path:
    """Where a subject's cycle records are written: private subjects → the private store."""
    return private_sibling(DEFAULT_STUDY_CYCLES_PATH) if is_private_subject(subject) else DEFAULT_STUDY_CYCLES_PATH


def load_study_cycles(path: Path = DEFAULT_STUDY_CYCLES_PATH, *, merge_private: bool = True) -> Dict[str, Any]:
    """Read cycle records. Reading a store also merges its private sibling, if any (sorted by
    finish time), so retention, prerequisites, and reviews see one history. Pass
    merge_private=False to read a single store raw — that is what writers must do."""
    store = _read_json(path, {"version": 1, "cycles": []})
    if merge_private and private_sibling(path).exists():
        private = _read_json(private_sibling(path), {"version": 1, "cycles": []})
        if private.get("cycles"):
            merged = list(store.get("cycles", [])) + [dict(c, private=True) for c in private["cycles"]]
            merged.sort(key=lambda c: c.get("finished_at") or "")
            store = dict(store, cycles=merged)
    return store


def redact_private_cycles(store: Dict[str, Any]) -> Dict[str, Any]:
    """A view of the cycle store safe for records that live in the public repo (the reflection
    digest): private lesson/subject ids become stable opaque labels. Scores stay — the runtime
    still reflects on having studied; what it studied stays on this machine."""
    import hashlib
    out = []
    for cycle in store.get("cycles", []):
        if cycle.get("private"):
            token = hashlib.sha1(str(cycle.get("lesson_id")).encode("utf-8")).hexdigest()[:8]
            cycle = dict(cycle, lesson_id=f"private-lesson-{token}", subject_id="private-subject",
                         scope="private", sources=[])
        out.append(cycle)
    return dict(store, cycles=out)


def save_study_cycles(store: Dict[str, Any], path: Path = DEFAULT_STUDY_CYCLES_PATH) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(store, indent=2), encoding="utf-8")


def find_lesson(curriculum: Dict[str, Any], lesson_id: str) -> Optional[Dict[str, Any]]:
    """Return {subject, lesson} for a lesson id, or None."""
    for subject in curriculum.get("subjects", []):
        for lesson in subject.get("lessons", []):
            if lesson.get("id") == lesson_id:
                return {"subject": subject, "lesson": lesson}
    return None


def passed_lessons(cycles_store: Dict[str, Any]) -> set:
    return {
        c.get("lesson_id")
        for c in cycles_store.get("cycles", [])
        if c.get("status") == "passed"
    }


def unmet_prerequisites(lesson: Dict[str, Any], cycles_store: Dict[str, Any]) -> List[str]:
    done = passed_lessons(cycles_store)
    return [p for p in lesson.get("prerequisites", []) if p not in done]


def chunk_text(text: str, target_chars: int = 600) -> List[str]:
    """Deterministic paragraph chunking: split on blank lines, merge adjacent paragraphs
    until the target size. Never splits inside a paragraph."""
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if current and len(candidate) > target_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def read_source(source: str) -> str:
    """Read a lesson source file. Relative paths resolve from the repository root."""
    path = Path(source)
    if not path.is_absolute():
        path = REPO_ROOT / source
    return path.read_text(encoding="utf-8")


def grade_recall(
    quiz: List[Dict[str, Any]],
    retrieve: Callable[[str], List[Dict[str, Any]]],
    k: int = 5,
) -> Dict[str, Any]:
    """Deterministic recall grading (no LLM, no self-grading): for each quiz question,
    call `retrieve(question)` and find the first ranked memory whose text contains every
    operator-authored `expect` term (case-insensitive). Records hit@k and rank."""
    per_question = []
    hits = 0
    for item in quiz:
        expect = [str(t).lower() for t in item.get("expect", []) if str(t).strip()]
        results = retrieve(item.get("question", ""))[:k]
        rank = None
        for i, memory in enumerate(results, start=1):
            text = str(memory.get("summary_text", "")).lower()
            if expect and all(term in text for term in expect):
                rank = i
                break
        hit = rank is not None
        hits += 1 if hit else 0
        per_question.append({"id": item.get("id"), "hit": hit, "rank": rank})
    total = len(quiz) or 1
    return {"k": k, "score": round(hits / total, 4), "hits": hits,
            "questions": len(quiz), "per_question": per_question}


def grade_comprehension(
    quiz: List[Dict[str, Any]],
    answer: Callable[[str], str],
) -> Dict[str, Any]:
    """Deterministic comprehension grading (ADR 0013: the model never grades itself).
    `answer(question)` produces the model's answer; a question is correct when the answer
    contains every operator-authored key term (item `answer_expect`, falling back to
    `expect`), case-insensitive."""
    per_question = []
    hits = 0
    for item in quiz:
        terms = [t for t in (item.get("answer_expect") or item.get("expect") or [])
                 if (isinstance(t, list) and t) or str(t).strip()]
        text = str(answer(item.get("question", "")) or "")
        lowered = text.lower()

        def _satisfied(term) -> bool:
            if isinstance(term, list):  # OR-group: any synonym satisfies
                return any(str(alt).lower() in lowered for alt in term)
            return str(term).lower() in lowered

        hit = bool(terms) and all(_satisfied(term) for term in terms)
        hits += 1 if hit else 0
        per_question.append({"id": item.get("id"), "hit": hit,
                             "answer_preview": text.strip()[:160]})
    total = len(quiz) or 1
    return {"score": round(hits / total, 4), "hits": hits,
            "questions": len(quiz), "per_question": per_question}


def compose_quiz(lesson: Dict[str, Any], curriculum: Dict[str, Any]) -> List[Dict[str, Any]]:
    """XI-B cumulative quizzes: the lesson's own questions plus every question from the
    lessons named in `review_lessons` (interference check — new learning must not degrade
    old recall). Review items get namespaced ids and carry their origin lesson."""
    items: List[Dict[str, Any]] = []
    for item in lesson.get("quiz", []):
        entry = dict(item)
        entry["origin"] = lesson.get("id")
        items.append(entry)
    for review_id in lesson.get("review_lessons", []):
        found = find_lesson(curriculum, review_id)
        if not found:
            continue
        for item in found["lesson"].get("quiz", []):
            entry = dict(item)
            entry["id"] = f"{review_id}:{item.get('id')}"
            entry["origin"] = review_id
            items.append(entry)
    return items


def section_scores(result: Dict[str, Any], items: List[Dict[str, Any]], own_lesson_id: str) -> Dict[str, Any]:
    """Split a graded result into own-lesson vs review sections (None when no review items)."""
    origin_by_id = {i.get("id"): i.get("origin") for i in items}
    own_hits = own_total = review_hits = review_total = 0
    for q in result.get("per_question", []):
        origin = origin_by_id.get(q.get("id"))
        if origin == own_lesson_id:
            own_total += 1
            own_hits += 1 if q.get("hit") else 0
        else:
            review_total += 1
            review_hits += 1 if q.get("hit") else 0
    return {
        "own": round(own_hits / own_total, 4) if own_total else None,
        "review": round(review_hits / review_total, 4) if review_total else None,
    }


def retention_report(cycles_store: Dict[str, Any]) -> List[Dict[str, Any]]:
    """XI-B retention: per lesson, the score history across every cycle — the raw series
    of the retention curve. Growth (and decay) is observed, not assumed."""
    by_lesson: Dict[str, List[Dict[str, Any]]] = {}
    for cycle in cycles_store.get("cycles", []):
        lesson_id = cycle.get("lesson_id")
        if not lesson_id:
            continue
        comp = cycle.get("comprehension") or {}
        by_lesson.setdefault(lesson_id, []).append({
            "finished_at": cycle.get("finished_at"),
            "recall": (cycle.get("recall_post") or {}).get("score"),
            "comprehension": comp.get("score"),
            "status": cycle.get("status"),
            "chunks_written": cycle.get("chunks_written", 0),
        })
    report = []
    for lesson_id, history in by_lesson.items():
        history.sort(key=lambda h: h.get("finished_at") or "")
        recalls = [h["recall"] for h in history if h.get("recall") is not None]
        report.append({
            "lesson_id": lesson_id,
            "attempts": len(history),
            "first_recall": recalls[0] if recalls else None,
            "latest_recall": recalls[-1] if recalls else None,
            "retention_delta": round(recalls[-1] - recalls[0], 4) if len(recalls) >= 2 else None,
            "history": history,
        })
    report.sort(key=lambda r: r["lesson_id"])
    return report


def load_adapters(path: Path = DEFAULT_ADAPTERS_PATH) -> Dict[str, Any]:
    if not Path(path).exists():
        return {"version": 1, "adapters": []}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_adapters(store: Dict[str, Any], path: Path = DEFAULT_ADAPTERS_PATH) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(store, indent=2), encoding="utf-8")


def set_adapter_status(store: Dict[str, Any], adapter_id: str, status: str, timestamp: str) -> Optional[Dict[str, Any]]:
    """Adapter lifecycle: candidate -> trained -> active -> retired. Activation follows the
    Model-Lock pattern — explicit, recorded, and single-active-per-subject (activating one
    retires any other active adapter for the same subject)."""
    target = next((a for a in store.get("adapters", []) if a.get("id") == adapter_id), None)
    if target is None:
        return None
    if status == "active":
        for other in store.get("adapters", []):
            if other is not target and other.get("subject_id") == target.get("subject_id")                     and other.get("status") == "active":
                other["status"] = "retired"
                other["retired_at"] = timestamp
        target["activated_at"] = timestamp
    target["status"] = status
    target["updated_at"] = timestamp
    return target
