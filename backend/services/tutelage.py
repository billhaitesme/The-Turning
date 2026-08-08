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
# Lesson source paths are relative to the repository root (backend/..).
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_curriculum(path: Path = DEFAULT_CURRICULUM_PATH) -> Dict[str, Any]:
    if not Path(path).exists():
        return {"version": 1, "subjects": []}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_study_cycles(path: Path = DEFAULT_STUDY_CYCLES_PATH) -> Dict[str, Any]:
    if not Path(path).exists():
        return {"version": 1, "cycles": []}
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
