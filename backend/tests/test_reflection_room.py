"""Deterministic tests for Epoch XII — the reflection room (ADR 0025).

Digest math over synthetic stores, and the full cycle with a stubbed composer:
observation lands in the reserved self-reflection room with its digest as provenance,
and the cycle record is persisted. Temp DB + temp stores; no Ollama.
"""
import sqlite3

import app
from services import reflection_room, tutelage
from benchmarks.recall_benchmark import stub_embedding


def _digest_fixture():
    return dict(
        since=None,
        study_cycles={"cycles": [
            {"lesson_id": "l1", "status": "passed", "finished_at": "2026-08-08T10:00:00Z",
             "recall_post": {"score": 1.0},
             "comprehension": {"score": 0.9, "sections": {"own": 1.0, "review": 0.8}}},
            {"lesson_id": "l2", "status": "failed", "finished_at": "2026-08-08T11:00:00Z",
             "recall_post": {"score": 0.5}, "comprehension": None},
        ]},
        supersession_candidates=[
            {"status": "pending"},
            {"status": "approved", "resolved_at": "2026-08-08T12:00:00Z"},
        ],
        memory_events=[
            {"event": "rescope", "created_at": "2026-08-08T13:00:00Z"},
            {"event": "restore", "created_at": "2026-08-08T13:30:00Z"},
        ],
        adapters={"adapters": [
            {"status": "candidate", "created_at": "2026-08-08T12:30:00Z"},
            {"status": "active", "created_at": "2026-08-07T12:00:00Z"},
        ]},
        reflection_cycles={"cycles": [{"id": "r1"}]},
    )


def test_digest_is_deterministic_and_traceable():
    digest = reflection_room.build_digest(**_digest_fixture())
    assert digest["study"]["cycles"] == 2
    assert digest["study"]["lessons_passed"] == ["l1"]
    assert digest["study"]["lessons_failed"] == ["l2"]
    assert digest["study"]["avg_recall"] == 0.75
    assert digest["study"]["avg_comprehension"] == 0.9
    assert digest["study"]["review_interference_min"] == 0.8
    assert digest["memory_governance"]["supersessions_pending"] == 1
    assert digest["memory_governance"]["supersessions_resolved"] == 1
    assert digest["memory_governance"]["operator_corrections"] == 2
    assert digest["consolidation"]["gated_runs"] == 2  # every registry entry is a durable gated-run record
    assert digest["consolidation"]["adapters_total"] == 2
    assert digest["consolidation"]["adapters_active"] == 1
    assert digest["reflection"]["prior_observations"] == 1
    # window filter: nothing before `since` counts
    windowed = reflection_room.build_digest(**{**_digest_fixture(), "since": "2026-08-08T10:30:00Z"})
    assert windowed["study"]["cycles"] == 1 and windowed["study"]["lessons_passed"] == []


def test_digest_summary_lines_carry_the_facts():
    lines = reflection_room.digest_summary_lines(reflection_room.build_digest(**_digest_fixture()))
    joined = " ".join(lines)
    assert "l1" in joined and "l2" in joined
    assert "1 supersession candidate(s)" in joined
    assert "2 operator correction(s)" in joined
    assert "2 operator-gated run(s)" in joined


def test_reflection_cycle_writes_only_the_room_and_records(monkeypatch, tmp_path):
    database = tmp_path / "reflect.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", stub_embedding)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", 0.0)
    monkeypatch.setattr(tutelage, "DEFAULT_STUDY_CYCLES_PATH", tmp_path / "sc.json")
    monkeypatch.setattr(tutelage, "DEFAULT_ADAPTERS_PATH", tmp_path / "ad.json")
    monkeypatch.setattr(reflection_room, "DEFAULT_REFLECTION_CYCLES_PATH", tmp_path / "rc.json")
    monkeypatch.setattr(app, "compose_reflection",
                        lambda model, lines: "I studied, I was corrected, and I remember it.")
    app.init_db()

    record = app.run_reflection_cycle()

    # the observation landed in the reserved room, with the digest as provenance
    rows = app.browse_memories(scope=reflection_room.REFLECTION_SCOPE, status="all")
    assert len(rows) == 1
    assert rows[0]["kind"] == "self_observation"
    assert rows[0]["summary_text"].startswith("I studied")
    assert rows[0]["source_text"].startswith("digest: ")

    # the cycle record persisted with digest + lines + preview
    store = reflection_room.load_reflection_cycles(reflection_room.DEFAULT_REFLECTION_CYCLES_PATH)
    assert len(store["cycles"]) == 1
    assert store["cycles"][0]["digest"]["study"]["cycles"] == 0
    assert store["cycles"][0]["observation_preview"].startswith("I studied")
    assert record["digest_lines"]

    # a second cycle sees the first as a prior observation (the identity curve accumulates)
    record2 = app.run_reflection_cycle()
    assert record2["digest"]["reflection"]["prior_observations"] == 1
