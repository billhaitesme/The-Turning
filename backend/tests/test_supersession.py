"""Deterministic tests for Epoch X write-time supersession.

ADR 0018 (mechanism, reversible flags) upgraded by ADR 0021 (robust form): a prior fact is
auto-superseded only when the new text DECLARES the change; undeclared high-similarity
collisions become pending candidates for operator review, and nothing is hidden from
recall until approved. Temp DB + controlled embedder; no Ollama.
"""
import sqlite3

import app


def _setup(monkeypatch, tmp_path, threshold):
    database = tmp_path / "sup.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    def fake_embed(text):
        t = str(text).lower()
        if "coffee" in t:
            return [0.0, 1.0, 0.0]
        if "port" in t or "backend" in t or "8000" in t or "8001" in t:
            return [1.0, 0.0, 0.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", fake_embed)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", threshold)
    app.init_db()


def _rows(sql):
    conn = app.get_db()
    rows = [dict(r) for r in conn.execute(sql).fetchall()]
    conn.close()
    return rows


def test_declared_change_auto_supersedes(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.9)
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="the backend moved to port 8001")

    rows = _rows("SELECT summary_text, superseded FROM memories")
    assert len(rows) == 2  # both kept — reversible, never deleted
    superseded = [r for r in rows if r["superseded"]]
    assert len(superseded) == 1 and "8000" in superseded[0]["summary_text"]

    cands = _rows("SELECT * FROM supersession_candidates")
    assert len(cands) == 1 and cands[0]["status"] == "auto" and cands[0]["declared"] == 1

    recalled = app.search_memories(query="what port is the backend on", conversation_id="c1", user_id="u1")
    assert len(recalled) == 1 and "8001" in recalled[0]["summary_text"]


def test_undeclared_collision_becomes_pending_and_hides_nothing(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.9)
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8001")  # no change marker

    rows = _rows("SELECT superseded FROM memories")
    assert all(not r["superseded"] for r in rows)  # nothing auto-hidden
    cands = _rows("SELECT * FROM supersession_candidates")
    assert len(cands) == 1 and cands[0]["status"] == "pending" and cands[0]["declared"] == 0
    # both remain recallable until the operator decides
    assert len(app.search_memories(query="port", conversation_id="c1", user_id="u1")) == 2


def test_approve_and_reject_pending_candidate(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.9)
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8001")
    cand = app.list_supersession_candidates()[0]

    assert app.resolve_supersession_candidate(cand["id"], approve=True)
    recalled = app.search_memories(query="port", conversation_id="c1", user_id="u1")
    assert len(recalled) == 1 and "8001" in recalled[0]["summary_text"]
    assert app.list_supersession_candidates() == []            # no longer pending
    assert not app.resolve_supersession_candidate(cand["id"], approve=True)  # already resolved

    # rejection path: new pair, reject -> both stay active
    app.save_memory(conversation_id="c1", user_id="u1", kind="preference",
                    source_text="s", summary_text="coffee black")
    app.save_memory(conversation_id="c1", user_id="u1", kind="preference",
                    source_text="s", summary_text="coffee with cream")
    cand2 = app.list_supersession_candidates()[0]
    assert app.resolve_supersession_candidate(cand2["id"], approve=False)
    texts = {m["summary_text"] for m in app.search_memories(query="coffee", conversation_id="c1", user_id="u1")}
    assert {"coffee black", "coffee with cream"} <= texts  # rejected -> both stay active


def test_complementary_and_cross_kind_and_cross_room_produce_nothing(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.9)
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="operator likes coffee")           # orthogonal
    app.save_memory(conversation_id="c1", user_id="u1", kind="technical",
                    source_text="s", summary_text="the backend moved to port 8001")  # other kind
    app.save_memory(conversation_id="c1", user_id="u1", kind="config", scope="room-b",
                    source_text="s", summary_text="the backend moved to port 8001")  # other room

    rows = _rows("SELECT superseded FROM memories")
    assert all(not r["superseded"] for r in rows)
    assert _rows("SELECT * FROM supersession_candidates") == []


def test_supersession_off_by_default(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.0)  # default
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="the backend moved to port 8001")

    rows = _rows("SELECT superseded FROM memories")
    assert all(not r["superseded"] for r in rows)
    assert _rows("SELECT * FROM supersession_candidates") == []
    assert len(app.search_memories(query="port", conversation_id="c1", user_id="u1")) == 2


def test_change_marker_detection():
    yes = [
        "The deadline is now Friday.",
        "We switched to PowerShell.",
        "The backend moved to port 8001.",
        "The operator no longer uses bash.",
        "The service was renamed to Bridge Zero.",
        "It was replaced by the new adapter.",
    ]
    no = [
        "The deadline is Friday.",
        "The backend is FastAPI.",
        "The backend is Python.",
        "Now, about the deadline...",   # bare 'now' without a change frame
        "The operator likes coffee.",
    ]
    for text in yes:
        assert app._declares_change(text), text
    for text in no:
        assert not app._declares_change(text), text
