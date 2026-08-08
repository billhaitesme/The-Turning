"""Deterministic tests for Epoch XI Tutelage, slice 1 (ADR 0013).

Full study cycle against a temp curriculum, temp DB, and the deterministic stub embedder
(real retrieval semantics, no Ollama): ingest -> scoped room memories with provenance ->
pre/post recall test -> auditable cycle record -> prerequisite gating.
"""
import json
import sqlite3

import pytest

import app
from benchmarks.recall_benchmark import stub_embedding
from services import tutelage


LESSON_TEXT = """# Test Lesson

The capital of Freedonia is Zubrowka City, which sits on the Zubrowka river.

The national bird of Freedonia is the crested penguin, famous for its amber crest.

Freedonia measures distance in flurbs, and one flurb equals seven meters exactly.
"""

CURRICULUM = {
    "version": 1,
    "subjects": [{
        "id": "test-subject",
        "title": "Test Subject",
        "scope": "test-subject",
        "lessons": [
            {
                "id": "lesson-a",
                "title": "Lesson A",
                "prerequisites": [],
                "sources": [],  # filled per-test with an absolute temp path
                "pass_threshold": 0.6,
                "quiz": [
                    {"id": "q1", "question": "What is the capital of Freedonia?", "expect": ["zubrowka city"]},
                    {"id": "q2", "question": "What is the national bird of Freedonia?", "expect": ["crested penguin"]},
                    {"id": "q3", "question": "How long is one flurb?", "expect": ["seven meters"]},
                ],
            },
            {
                "id": "lesson-b",
                "title": "Lesson B",
                "prerequisites": ["lesson-a"],
                "sources": [],
                "pass_threshold": 0.6,
                "quiz": [{"id": "q1", "question": "anything", "expect": ["zubrowka city"]}],
            },
        ],
    }],
}


def _setup(monkeypatch, tmp_path):
    database = tmp_path / "tutelage.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", stub_embedding)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", 0.0)
    app.init_db()

    source = tmp_path / "lesson-a.md"
    source.write_text(LESSON_TEXT, encoding="utf-8")
    curriculum = json.loads(json.dumps(CURRICULUM))
    curriculum["subjects"][0]["lessons"][0]["sources"] = [str(source)]
    curriculum["subjects"][0]["lessons"][1]["sources"] = [str(source)]

    curriculum_path = tmp_path / "curriculum.json"
    curriculum_path.write_text(json.dumps(curriculum), encoding="utf-8")
    cycles_path = tmp_path / "study_cycles.json"
    monkeypatch.setattr(tutelage, "DEFAULT_CURRICULUM_PATH", curriculum_path)
    monkeypatch.setattr(tutelage, "DEFAULT_STUDY_CYCLES_PATH", cycles_path)


def test_full_cycle_learns_and_passes(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    record = app.run_study_cycle("lesson-a")

    assert record["recall_pre"]["score"] == 0.0          # knew nothing before
    assert record["recall_post"]["score"] == 1.0         # retrieves every fact after
    assert record["status"] == "passed"
    assert record["chunks_written"] >= 1
    assert record["sources"][0]["chunks"] == record["chunks_written"]

    # memories landed in the subject's room, kind=study, with per-chunk provenance
    rows = app.browse_memories(scope="test-subject", kind="study", status="all")
    assert len(rows) == record["chunks_written"]
    assert all("#chunk" in r["source_text"] for r in rows)

    # the lesson conversation carries the room
    meta = app.get_conversation_meta(record["conversation_id"])
    assert meta["scope"] == "test-subject"

    # the cycle record is persisted and passing unlocked the dependent lesson
    cycles = tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH)
    assert cycles["cycles"][0]["lesson_id"] == "lesson-a"
    assert tutelage.unmet_prerequisites(
        {"prerequisites": ["lesson-a"]}, cycles) == []


def test_prerequisite_gating_blocks_until_passed(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    with pytest.raises(PermissionError):
        app.run_study_cycle("lesson-b")
    app.run_study_cycle("lesson-a")
    record = app.run_study_cycle("lesson-b")  # now unlocked
    assert record["lesson_id"] == "lesson-b"


def test_unknown_lesson_raises(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    with pytest.raises(LookupError):
        app.run_study_cycle("no-such-lesson")


def test_chunking_is_deterministic_and_paragraph_safe():
    chunks = tutelage.chunk_text(LESSON_TEXT, target_chars=120)
    assert chunks == tutelage.chunk_text(LESSON_TEXT, target_chars=120)
    assert any("Zubrowka City" in c for c in chunks)
    # no paragraph is ever split
    for c in chunks:
        assert "capital of Freedonia is Zubrowka City" in c or "capital" not in c


def test_grade_recall_rank_and_miss():
    quiz = [{"id": "q1", "question": "capital?", "expect": ["zubrowka"]},
            {"id": "q2", "question": "missing?", "expect": ["not present anywhere"]}]
    memories = [{"summary_text": "filler"}, {"summary_text": "the capital is Zubrowka City"}]
    graded = tutelage.grade_recall(quiz, lambda q: memories, k=5)
    assert graded["per_question"][0]["hit"] and graded["per_question"][0]["rank"] == 2
    assert not graded["per_question"][1]["hit"]
    assert graded["score"] == 0.5
