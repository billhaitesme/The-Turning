"""Deterministic tests for Epoch X memory consolidation (ADR 0023).

The scan proposes near-duplicate memories (same kind/room/user, cosine >= floor) into the
supersession review queue, keeping the newest row as representative. It never auto-hides.
Temp DB + controlled embedder; no Ollama.
"""
import sqlite3

import app


def _setup(monkeypatch, tmp_path):
    database = tmp_path / "consol.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    # near-duplicates share a direction; "weather" rows are slight variants of each other
    def fake_embed(text):
        t = str(text).lower()
        if "weather" in t:
            return [1.0, 0.05 if "again" in t else 0.0, 0.0]
        if "deadline" in t:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", fake_embed)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", 0.0)  # write-scan off; consolidation only
    app.init_db()


def _save(summary, kind="user_request", scope=None, user="u1"):
    app.save_memory(conversation_id="c1", user_id=user, kind=kind,
                    source_text="s", summary_text=summary, scope=scope)


def test_scan_proposes_older_near_duplicates_keeping_newest(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _save("what is the weather")           # oldest
    _save("what is the weather again")     # near-dup
    _save("what is the weather right now") # newest -> representative
    _save("the deadline is Friday", kind="project")  # different kind, untouched

    summary = app.consolidation_scan(threshold=0.95)
    assert summary["proposed"] == 2 and summary["skipped_existing"] == 0

    pending = app.list_supersession_candidates()
    assert len(pending) == 2
    assert all(c["origin"] == "consolidation" and c["status"] == "pending" for c in pending)
    # nothing hidden yet: all four memories still active
    conn = app.get_db()
    active = conn.execute("SELECT COUNT(*) AS n FROM memories WHERE superseded = 0 OR superseded IS NULL").fetchone()["n"]
    conn.close()
    assert active == 4


def test_approve_consolidation_hides_duplicate_and_is_restorable(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _save("what is the weather")
    _save("what is the weather again")
    app.consolidation_scan(threshold=0.95)
    cand = app.list_supersession_candidates()[0]
    assert app.resolve_supersession_candidate(cand["id"], approve=True)
    superseded = app.browse_memories(status="superseded")
    assert len(superseded) == 1
    assert app.restore_memory(superseded[0]["id"])  # reversible


def test_scan_respects_kind_room_and_threshold_boundaries(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _save("what is the weather")
    _save("what is the weather", kind="assistant_response")   # same text, other kind
    _save("what is the weather", scope="room-b")              # same text, other room
    _save("the deadline is Friday", kind="user_request")      # dissimilar, same kind

    assert app.consolidation_scan(threshold=0.95)["proposed"] == 0

    # threshold boundary: the "again" variant sits just below 1.0; a stricter floor excludes it
    _save("what is the weather again")
    assert app.consolidation_scan(threshold=0.9999)["proposed"] == 0


def test_rescan_skips_existing_candidates(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _save("what is the weather")
    _save("what is the weather again")
    first = app.consolidation_scan(threshold=0.95)
    assert first["proposed"] == 1
    second = app.consolidation_scan(threshold=0.95)
    assert second["proposed"] == 0 and second["skipped_existing"] == 1
    assert len(app.list_supersession_candidates()) == 1  # no duplicate proposals


def test_invalid_threshold_rejected(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    try:
        app.consolidation_scan(threshold=1.5)
        assert False, "expected ValueError"
    except ValueError:
        pass
