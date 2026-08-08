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
                "review_lessons": ["lesson-a"],
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
    # deterministic study-seat: answers by echoing the retrieved notes (never hits Ollama)
    monkeypatch.setattr(app, "study_answer", lambda model, question, notes: " ".join(notes))
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


def test_comprehension_grades_and_gates(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    record = app.run_study_cycle("lesson-a")
    # note-echo answerer contains every key term -> full comprehension
    assert record["comprehension"]["score"] == 1.0
    assert record["comprehension"]["model"]
    assert record["status"] == "passed"

    # a failing study-seat fails the lesson even with perfect recall
    monkeypatch.setattr(app, "study_answer", lambda model, question, notes: "I do not know.")
    record2 = app.run_study_cycle("lesson-a")
    assert record2["recall_post"]["score"] == 1.0
    assert record2["comprehension"]["score"] == 0.0
    assert record2["status"] == "failed"

    # comprehension can be skipped (recall-only cycle)
    record3 = app.run_study_cycle("lesson-a", comprehension=False)
    assert record3["comprehension"] is None and record3["status"] == "passed"


def test_reingestion_is_idempotent(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    first = app.run_study_cycle("lesson-a")
    again = app.run_study_cycle("lesson-a")  # spaced-repetition re-run
    assert again["chunks_written"] == 0
    assert again["sources"][0].get("skipped") == "already ingested"
    rows = app.browse_memories(scope="test-subject", kind="study", status="all")
    assert len(rows) == first["chunks_written"]  # no duplicates
    assert again["recall_post"]["score"] == 1.0  # still retrievable


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


def test_cumulative_quiz_sections_and_interference(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    app.run_study_cycle("lesson-a")
    record = app.run_study_cycle("lesson-b")  # cumulative: reviews lesson-a's questions
    # 1 own + 3 review questions were graded
    assert record["recall_post"]["questions"] == 4
    assert record["recall_post"]["sections"]["own"] == 1.0
    assert record["recall_post"]["sections"]["review"] == 1.0
    assert record["status"] == "passed"

    # interference: perfect own-lesson answers but failed review section fails the lesson
    def selective_answer(model, question, notes):
        return " ".join(notes) if "anything" in question else "no idea"
    monkeypatch.setattr(app, "study_answer", selective_answer)
    record2 = app.run_study_cycle("lesson-b")
    assert record2["comprehension"]["sections"]["own"] == 1.0
    assert record2["comprehension"]["sections"]["review"] == 0.0
    assert record2["status"] == "failed"


def test_retention_report_tracks_history(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    app.run_study_cycle("lesson-a")
    app.run_study_cycle("lesson-a")  # spaced re-quiz (no re-ingest)
    report = tutelage.retention_report(tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH))
    entry = next(r for r in report if r["lesson_id"] == "lesson-a")
    assert entry["attempts"] == 2
    assert entry["first_recall"] == 1.0 and entry["latest_recall"] == 1.0
    assert entry["retention_delta"] == 0.0
    assert len(entry["history"]) == 2


def _approve_consolidation(subject_id):
    from services import tool_approval
    request = {
        "request_id": f"toolreq-consol-{subject_id}",
        "tool_name": "tutelage_consolidation",
        "arguments": {"subject_id": subject_id},
        "requested_by": "runtime",
        "session_id": "test",
        "status": "proposed",
        "goal_id": None,
        "plan_id": None,
        "decision_id": None,
        "approval_id": None,
        "created_at": "2026-08-08T00:00:00+00:00",
    }
    tool_approval.create_approval_request(request)
    tool_approval.approve_request(request["request_id"], approved_by="operator")


def test_consolidation_requires_and_consumes_approval(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(app, "DISTILLATION_DIR", tmp_path / "distillation")
    monkeypatch.setattr(tutelage, "DEFAULT_ADAPTERS_PATH", tmp_path / "adapters.json")
    app.run_study_cycle("lesson-a")

    # blocked without an approved gate
    with pytest.raises(PermissionError):
        app.run_consolidation("test-subject")

    # answers: two verified, one deliberately wrong -> filtered out of the artifact
    def selective_answer(model, question, notes):
        if "flurb" in question:
            return "no idea"
        return " ".join(notes)
    monkeypatch.setattr(app, "study_answer", selective_answer)

    _approve_consolidation("test-subject")
    entry = app.run_consolidation("test-subject")
    assert entry["status"] == "candidate"
    assert entry["pairs_count"] == 2 and entry["skipped_unverified"] == 1
    assert entry["source_lessons"] == ["lesson-a"]

    # the artifact is chat-format JSONL matching the training pipeline
    import json as _json
    lines = (tmp_path / "distillation" / f"{entry['id']}.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = _json.loads(lines[0])
    assert [m["role"] for m in first["messages"]] == ["system", "user", "assistant"]

    # single-use: the approval was consumed, a second run is blocked
    with pytest.raises(PermissionError):
        app.run_consolidation("test-subject")


def test_adapter_lifecycle_single_active_per_subject(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(tutelage, "DEFAULT_ADAPTERS_PATH", tmp_path / "adapters.json")
    store = {"version": 1, "adapters": [
        {"id": "a1", "subject_id": "s", "status": "active", "activated_at": "t0"},
        {"id": "a2", "subject_id": "s", "status": "trained"},
        {"id": "b1", "subject_id": "other", "status": "active"},
    ]}
    entry = tutelage.set_adapter_status(store, "a2", "active", "t1")
    assert entry["status"] == "active" and entry["activated_at"] == "t1"
    assert next(a for a in store["adapters"] if a["id"] == "a1")["status"] == "retired"
    assert next(a for a in store["adapters"] if a["id"] == "b1")["status"] == "active"  # other subject untouched
    assert tutelage.set_adapter_status(store, "missing", "active", "t2") is None


def test_strip_think_and_or_groups():
    # leaked thinking is removed whether closed or unterminated
    assert app._strip_think("<think>reasoning about zubrowka</think>The answer is Paris.") == "The answer is Paris."
    assert app._strip_think("<think>endless reasoning that never closes") == ""
    # OR-groups: a list entry is satisfied by any synonym; strings stay required
    quiz = [{"id": "q1", "question": "?", "answer_expect": [["recency", "newer fact"], "tie-break"]}]
    graded = tutelage.grade_comprehension(quiz, lambda q: "the newer fact wins the tie-break")
    assert graded["score"] == 1.0
    graded2 = tutelage.grade_comprehension(quiz, lambda q: "the newer fact wins")  # missing required string
    assert graded2["score"] == 0.0


def test_grade_recall_rank_and_miss():
    quiz = [{"id": "q1", "question": "capital?", "expect": ["zubrowka"]},
            {"id": "q2", "question": "missing?", "expect": ["not present anywhere"]}]
    memories = [{"summary_text": "filler"}, {"summary_text": "the capital is Zubrowka City"}]
    graded = tutelage.grade_recall(quiz, lambda q: memories, k=5)
    assert graded["per_question"][0]["hit"] and graded["per_question"][0]["rank"] == 2
    assert not graded["per_question"][1]["hit"]
    assert graded["score"] == 0.5
